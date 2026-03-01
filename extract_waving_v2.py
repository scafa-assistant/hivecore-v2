"""Extrahiert Winken-Animation aus Original-GLB.
Rechts: direkt aus GLB
Links: gespiegelt (L↔R Swap + Y/Z-Achsen negiert)
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

# BONE_MAP: GLB-Name → Motor-Name
# Erweitert fuer Meshy-GLB Naming (Spine01, Spine02, neck lowercase)
BONE_MAP = {
    'Head': 'head',
    'neck': 'neck',           # lowercase in Meshy-GLB!
    'Spine': 'spine',
    'Spine01': 'spine1',      # Meshy: "01" statt "1"
    'Spine02': 'spine2',      # Meshy: "02" statt "2"
    'Hips': 'hips',
    'LeftShoulder': 'shoulder_L',
    'RightShoulder': 'shoulder_R',
    'LeftArm': 'upper_arm_L',
    'RightArm': 'upper_arm_R',
    'LeftForeArm': 'lower_arm_L',
    'RightForeArm': 'lower_arm_R',
    'LeftHand': 'hand_L',
    'RightHand': 'hand_R',
    'LeftUpLeg': 'upper_leg_L',
    'RightUpLeg': 'upper_leg_R',
    'LeftLeg': 'lower_leg_L',
    'RightLeg': 'lower_leg_R',
    'LeftFoot': 'foot_L',
    'RightFoot': 'foot_R',
}

# Amplitude-Skalierung pro Bone-Gruppe
# Oberkörper/Arme: voll, Beine/Füße: reduziert (additiv auf idle)
AMPLITUDE = {
    'head': 1.0, 'neck': 1.0,
    'spine': 1.0, 'spine1': 1.0, 'spine2': 1.0,
    'hips': 1.0,
    'shoulder_L': 1.0, 'shoulder_R': 1.0,
    'upper_arm_L': 1.0, 'upper_arm_R': 1.0,
    'lower_arm_L': 1.0, 'lower_arm_R': 1.0,
    'hand_L': 1.0, 'hand_R': 1.0,
    'upper_leg_L': 0.4, 'upper_leg_R': 0.4,
    'lower_leg_L': 0.4, 'lower_leg_R': 0.4,
    'foot_L': 0.4, 'foot_R': 0.4,
}

# Spiegelung: L↔R Bone-Mapping
MIRROR_MAP = {
    'shoulder_L': 'shoulder_R', 'shoulder_R': 'shoulder_L',
    'upper_arm_L': 'upper_arm_R', 'upper_arm_R': 'upper_arm_L',
    'lower_arm_L': 'lower_arm_R', 'lower_arm_R': 'lower_arm_L',
    'hand_L': 'hand_R', 'hand_R': 'hand_L',
    'upper_leg_L': 'upper_leg_R', 'upper_leg_R': 'upper_leg_L',
    'lower_leg_L': 'lower_leg_R', 'lower_leg_R': 'lower_leg_L',
    'foot_L': 'foot_R', 'foot_R': 'foot_L',
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
        if path_type == 'scale':
            continue  # scale nicht relevant
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

    print(f"  Mapped bones: {sorted(raw.keys())}")

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
            amp = AMPLITUDE.get(bone, 1.0)

            if 'rotation' in paths:
                times = paths['rotation']['times']
                rots = paths['rotation']['values']
                idx = min(range(len(times)), key=lambda i: abs(times[i] - t))
                euler = quat_to_euler(rots[idx])
                ref = ref_rot.get(bone, (0, 0, 0))
                drx = round((euler[0] - ref[0]) * amp, 1)
                dry = round((euler[1] - ref[1]) * amp, 1)
                drz = round((euler[2] - ref[2]) * amp, 1)
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
                if abs(dtx) >= 0.01:
                    vals['tx'] = dtx
                if abs(dty) >= 0.01:
                    vals['ty'] = dty
                if abs(dtz) >= 0.01:
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
    hips_ty = [kf['bones'].get('hips', {}).get('ty', 0) for kf in keyframes]
    hips_tz = [kf['bones'].get('hips', {}).get('tz', 0) for kf in keyframes]
    print(f"    Hips TX: {min(hips_tx):.2f} to {max(hips_tx):.2f}")
    print(f"    Hips TY: {min(hips_ty):.2f} to {max(hips_ty):.2f}")
    print(f"    Hips TZ: {min(hips_tz):.2f} to {max(hips_tz):.2f}")

    return entry


def mirror_entry(entry, new_id):
    """Spiegelt eine Motor-Animation L↔R."""
    mirrored = {
        'id': new_id,
        'category': entry['category'],
        'type': entry['type'],
        'duration_ms': entry['duration_ms'],
        'easing': entry['easing'],
        'loopable': entry['loopable'],
        'blendable': entry['blendable'],
        'glb_fallback': None,
        'keyframes': [],
    }
    for kf in entry['keyframes']:
        new_bones = {}
        for bone, vals in kf['bones'].items():
            # Bone-Name spiegeln (L↔R)
            new_bone = MIRROR_MAP.get(bone, bone)
            new_vals = {}
            for key, val in vals.items():
                if key in ('ry', 'rz', 'tx', 'tz'):
                    # Y-Rotation, Z-Rotation, X-Translation, Z-Translation: Vorzeichen tauschen
                    new_vals[key] = round(-val, 2) if key in ('tx', 'tz') else round(-val, 1)
                else:
                    new_vals[key] = val
            if new_vals:
                new_bones[new_bone] = new_vals
        if new_bones:
            mirrored['keyframes'].append({'t': kf['t'], 'bones': new_bones})

    print(f"  {new_id}: {len(mirrored['keyframes'])} keyframes (mirrored)")
    return mirrored


if __name__ == '__main__':
    print("Extrahiere Winken-rechts aus Original-GLB...")
    winken_r = extract_glb(
        r'C:\DEV\Avatar-glb\Winken\Meshy_AI_Animation_Wave_for_Help_2_withSkin.glb',
        'MOT_WAVE',
    )

    print("\nSpiegele fuer Winken-links...")
    winken_l = mirror_entry(winken_r, 'MOT_WAVE_LEFT')

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
        data = json.load(f)
    wr = data['motor_vocabulary']['words']['winken']
    wl = data['motor_vocabulary']['words']['winken_links']
    print(f"\nJSON OK — motor_vocabulary.json aktualisiert")
    print(f"  winken: {len(wr['keyframes'])} KF, {wr['duration_ms']}ms")
    print(f"  winken_links: {len(wl['keyframes'])} KF, {wl['duration_ms']}ms")
