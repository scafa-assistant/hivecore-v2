"""Extrahiert waving_right.glb und waving_left.glb als Motor-Keyframes.
Self-relative Deltas (Frame 0 als Referenz) + Hips-Translation.
"""
import struct, json, math

def load_glb(path):
    with open(path, 'rb') as f:
        magic, version, length = struct.unpack('<III', f.read(12))
        json_len, json_type = struct.unpack('<II', f.read(8))
        json_data = json.loads(f.read(json_len))
        bin_len, bin_type = struct.unpack('<II', f.read(8))
        bin_data = f.read(bin_len)
    return json_data, bin_data

def read_accessor(gltf, bin_data, idx):
    acc = gltf['accessors'][idx]
    bv = gltf['bufferViews'][acc['bufferView']]
    offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    count = acc['count']
    ctype = acc['componentType']
    dtype = {5126: 'f', 5123: 'H', 5125: 'I'}[ctype]
    size = struct.calcsize(dtype)
    atype = acc['type']
    components = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[atype]
    stride = bv.get('byteStride', size * components)
    result = []
    for i in range(count):
        pos = offset + i * stride
        vals = struct.unpack_from(f'<{components}{dtype}', bin_data, pos)
        result.append(vals if components > 1 else vals[0])
    return result

def quat_to_euler(q):
    x, y, z, w = q
    sinr = 2 * (w * x + y * z)
    cosr = 1 - 2 * (x * x + y * y)
    rx = math.atan2(sinr, cosr)
    sinp = 2 * (w * y - z * x)
    sinp = max(-1, min(1, sinp))
    ry = math.asin(sinp)
    siny = 2 * (w * z + x * y)
    cosy = 1 - 2 * (y * y + z * z)
    rz = math.atan2(siny, cosy)
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))

BONE_MAP = {
    'Head': 'head', 'Neck': 'neck',
    'Spine': 'spine', 'Spine1': 'spine1', 'Spine2': 'spine2',
    'Hips': 'hips',
    'LeftShoulder': 'shoulder_L', 'RightShoulder': 'shoulder_R',
    'LeftArm': 'upper_arm_L', 'RightArm': 'upper_arm_R',
    'LeftForeArm': 'lower_arm_L', 'RightForeArm': 'lower_arm_R',
    'LeftHand': 'hand_L', 'RightHand': 'hand_R',
    'LeftUpLeg': 'upper_leg_L', 'RightUpLeg': 'upper_leg_R',
    'LeftLeg': 'lower_leg_L', 'RightLeg': 'lower_leg_R',
    'LeftFoot': 'foot_L', 'RightFoot': 'foot_R',
    'LeftEye': 'eye_L', 'RightEye': 'eye_R',
}

def extract_glb(path, word_id, category='gesture'):
    gltf, bin_data = load_glb(path)
    nodes = gltf.get('nodes', [])
    node_names = {i: n.get('name', '') for i, n in enumerate(nodes)}
    anim = gltf['animations'][0]
    channels = anim['channels']
    samplers = anim['samplers']

    raw = {}
    for ch in channels:
        node_idx = ch['target'].get('node', -1)
        path_type = ch['target']['path']
        bone_glb = node_names.get(node_idx, '')
        bone_motor = BONE_MAP.get(bone_glb)
        if not bone_motor:
            continue
        sampler = samplers[ch['sampler']]
        times = read_accessor(gltf, bin_data, sampler['input'])
        values = read_accessor(gltf, bin_data, sampler['output'])
        if bone_motor not in raw:
            raw[bone_motor] = {}
        raw[bone_motor][path_type] = {'times': times, 'values': values}

    # Frame 0 als Referenz
    ref_rot = {}
    ref_trans = {}
    for bone, paths in raw.items():
        if 'rotation' in paths:
            ref_rot[bone] = quat_to_euler(paths['rotation']['values'][0])
        if 'translation' in paths:
            ref_trans[bone] = paths['translation']['values'][0]

    # Alle Zeitpunkte sammeln
    all_times = set()
    for bone, paths in raw.items():
        if 'rotation' in paths:
            all_times.update(paths['rotation']['times'])
    all_times = sorted(all_times)
    duration_ms = int(all_times[-1] * 1000)

    keyframes = []
    for t in all_times:
        bones_kf = {}
        for bone, paths in raw.items():
            vals = {}

            if 'rotation' in paths:
                times = paths['rotation']['times']
                rots = paths['rotation']['values']
                idx = min(range(len(times)), key=lambda i: abs(times[i] - t))
                euler = quat_to_euler(rots[idx])
                ref = ref_rot.get(bone, (0, 0, 0))
                drx = round(euler[0] - ref[0], 1)
                dry = round(euler[1] - ref[1], 1)
                drz = round(euler[2] - ref[2], 1)
                if abs(drx) >= 0.5:
                    vals['rx'] = drx
                if abs(dry) >= 0.5:
                    vals['ry'] = dry
                if abs(drz) >= 0.5:
                    vals['rz'] = drz

            if bone == 'hips' and 'translation' in paths:
                times = paths['translation']['times']
                trans = paths['translation']['values']
                idx = min(range(len(times)), key=lambda i: abs(times[i] - t))
                ref = ref_trans.get(bone, (0, 0, 0))
                dtx = round(trans[idx][0] - ref[0], 2)
                dty = round(trans[idx][1] - ref[1], 2)
                dtz = round(trans[idx][2] - ref[2], 2)
                if abs(dtx) >= 0.1:
                    vals['tx'] = dtx
                if abs(dty) >= 0.1:
                    vals['ty'] = dty
                if abs(dtz) >= 0.1:
                    vals['tz'] = dtz

            if vals:
                bones_kf[bone] = vals

        if bones_kf:
            keyframes.append({
                't': round(t / all_times[-1], 3),
                'bones': bones_kf,
            })

    entry = {
        'id': word_id,
        'category': category,
        'type': 'sequence',
        'duration_ms': duration_ms,
        'keyframes': keyframes,
        'easing': 'ease_in_out',
        'loopable': False,
        'blendable': True,
        'glb_fallback': None,
    }

    print(f"  {word_id}: {len(keyframes)} keyframes, {duration_ms}ms, {len(raw)} bones")
    hips_tx = [kf['bones'].get('hips', {}).get('tx', 0) for kf in keyframes]
    hips_tz = [kf['bones'].get('hips', {}).get('tz', 0) for kf in keyframes]
    if any(hips_tx) or any(hips_tz):
        print(f"    Hips TX: {min(hips_tx):.2f} to {max(hips_tx):.2f}")
        print(f"    Hips TZ: {min(hips_tz):.2f} to {max(hips_tz):.2f}")

    return entry


if __name__ == '__main__':
    print("Extrahiere waving_right.glb...")
    winken_r = extract_glb(
        r'C:\DEV\EgonsDash\assets\3d\adam\waving_right.glb',
        'MOT_WAVE',
    )

    print("Extrahiere waving_left.glb...")
    winken_l = extract_glb(
        r'C:\DEV\EgonsDash\assets\3d\adam\waving_left.glb',
        'MOT_WAVE_LEFT',
    )

    # In motor_vocabulary.json einsetzen
    with open('config/motor_vocabulary.json', 'r', encoding='utf-8') as f:
        v = json.load(f)

    words = v['motor_vocabulary']['words']
    words['winken'] = winken_r
    words['winken_links'] = winken_l

    with open('config/motor_vocabulary.json', 'w', encoding='utf-8') as f:
        json.dump(v, f, indent=2, ensure_ascii=False)

    # Verify
    with open('config/motor_vocabulary.json', 'r', encoding='utf-8') as f:
        json.load(f)
    print("JSON OK — motor_vocabulary.json aktualisiert")
