"""Stellt die alten Winken-Daten wieder her und fuegt nur Hips-Translation hinzu.
Fixe spine_0→spine, spine_1→spine1, spine_2→spine2.
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


def extract_hips_translation(glb_path):
    """Extrahiert NUR die Hips-Translation aus der GLB."""
    gltf, bin_data = load_glb(glb_path)
    nodes = gltf.get('nodes', [])
    node_names = {i: n.get('name', '') for i, n in enumerate(nodes)}
    anim = gltf['animations'][0]
    channels = anim['channels']
    samplers = anim['samplers']

    hips_trans = None
    hips_times = None
    for ch in channels:
        node_idx = ch['target'].get('node', -1)
        path_type = ch['target']['path']
        bone_name = node_names.get(node_idx, '')
        if bone_name == 'Hips' and path_type == 'translation':
            sampler = samplers[ch['sampler']]
            hips_times = read_accessor(gltf, bin_data, sampler['input'])
            hips_trans = read_accessor(gltf, bin_data, sampler['output'])
            break

    if not hips_trans:
        print("  WARNUNG: Keine Hips-Translation gefunden!")
        return None, None

    # Frame 0 als Referenz
    ref = hips_trans[0]
    duration = hips_times[-1]

    result = []
    for i, t in enumerate(hips_times):
        dtx = round(hips_trans[i][0] - ref[0], 2)
        dty = round(hips_trans[i][1] - ref[1], 2)
        dtz = round(hips_trans[i][2] - ref[2], 2)
        t_norm = round(t / duration, 3)
        entry = {'t': t_norm}
        if abs(dtx) >= 0.01:
            entry['tx'] = dtx
        if abs(dty) >= 0.01:
            entry['ty'] = dty
        if abs(dtz) >= 0.01:
            entry['tz'] = dtz
        result.append(entry)

    print(f"  Hips-Translation: {len(result)} Frames")
    tx_vals = [e.get('tx', 0) for e in result]
    ty_vals = [e.get('ty', 0) for e in result]
    tz_vals = [e.get('tz', 0) for e in result]
    print(f"    TX: {min(tx_vals):.2f} to {max(tx_vals):.2f}")
    print(f"    TY: {min(ty_vals):.2f} to {max(ty_vals):.2f}")
    print(f"    TZ: {min(tz_vals):.2f} to {max(tz_vals):.2f}")

    return result, duration


# Bone-Name Korrekturen
RENAME_MAP = {
    'spine_0': 'spine',
    'spine_1': 'spine1',
    'spine_2': 'spine2',
}

# L↔R Spiegelung
MIRROR_BONE = {
    'shoulder_L': 'shoulder_R', 'shoulder_R': 'shoulder_L',
    'upper_arm_L': 'upper_arm_R', 'upper_arm_R': 'upper_arm_L',
    'lower_arm_L': 'lower_arm_R', 'lower_arm_R': 'lower_arm_L',
    'hand_L': 'hand_R', 'hand_R': 'hand_L',
    'upper_leg_L': 'upper_leg_R', 'upper_leg_R': 'upper_leg_L',
    'lower_leg_L': 'lower_leg_R', 'lower_leg_R': 'lower_leg_L',
    'foot_L': 'foot_R', 'foot_R': 'foot_L',
}


def fix_entry(entry, hips_data):
    """Fixe Bone-Namen und merge Hips-Translation."""
    for kf in entry['keyframes']:
        # 1. Rename spine_0→spine etc.
        new_bones = {}
        for bone, vals in kf['bones'].items():
            new_name = RENAME_MAP.get(bone, bone)
            new_bones[new_name] = vals
        kf['bones'] = new_bones

        # 2. Merge Hips-Translation (naechster Zeitpunkt)
        if hips_data:
            t = kf['t']
            best = min(hips_data, key=lambda h: abs(h['t'] - t))
            hips = kf['bones'].get('hips', {})
            if 'tx' in best:
                hips['tx'] = best['tx']
            if 'ty' in best:
                hips['ty'] = best['ty']
            if 'tz' in best:
                hips['tz'] = best['tz']
            if hips:
                kf['bones']['hips'] = hips


def mirror_entry(entry, new_id):
    """Spiegelt L↔R."""
    import copy
    mirrored = copy.deepcopy(entry)
    mirrored['id'] = new_id

    for kf in mirrored['keyframes']:
        new_bones = {}
        for bone, vals in kf['bones'].items():
            new_bone = MIRROR_BONE.get(bone, bone)
            new_vals = {}
            for key, val in vals.items():
                if key in ('ry', 'rz'):
                    new_vals[key] = round(-val, 1)
                elif key in ('tx', 'tz'):
                    new_vals[key] = round(-val, 2)
                else:
                    new_vals[key] = val
            new_bones[new_bone] = new_vals
        kf['bones'] = new_bones

    return mirrored


if __name__ == '__main__':
    # 1. Alte Daten laden (vor meiner fehlerhaften Aenderung)
    print("Lade alte Winken-Daten (HEAD~1)...")
    with open('C:/Users/Max/old_vocab.json', 'r', encoding='utf-8') as f:
        old = json.load(f)
    old_winken = old['motor_vocabulary']['words']['winken']
    print(f"  winken: {len(old_winken['keyframes'])} KF, {old_winken['duration_ms']}ms")

    # 2. Hips-Translation aus GLB extrahieren
    print("\nExtrahiere Hips-Translation aus Original-GLB...")
    hips_data, duration = extract_hips_translation(
        r'C:\DEV\Avatar-glb\Winken\Meshy_AI_Animation_Wave_for_Help_2_withSkin.glb'
    )

    # 3. Fix old entry: rename bones + add hips translation
    print("\nFixe winken: Bone-Namen + Hips-Translation...")
    fix_entry(old_winken, hips_data)

    # Verify bones
    bones = set()
    for kf in old_winken['keyframes']:
        bones.update(kf['bones'].keys())
    print(f"  Bones: {sorted(bones)}")

    hips_tx = [kf['bones'].get('hips', {}).get('tx', 0) for kf in old_winken['keyframes']]
    hips_tz = [kf['bones'].get('hips', {}).get('tz', 0) for kf in old_winken['keyframes']]
    print(f"  Hips TX: {min(hips_tx):.2f} to {max(hips_tx):.2f}")
    print(f"  Hips TZ: {min(hips_tz):.2f} to {max(hips_tz):.2f}")

    # 4. Mirror fuer winken_links
    print("\nSpiegele fuer winken_links...")
    winken_links = mirror_entry(old_winken, 'MOT_WAVE_LEFT')
    print(f"  winken_links: {len(winken_links['keyframes'])} KF")

    # 5. In aktuelle vocab einsetzen
    with open('config/motor_vocabulary.json', 'r', encoding='utf-8') as f:
        vocab = json.load(f)
    vocab['motor_vocabulary']['words']['winken'] = old_winken
    vocab['motor_vocabulary']['words']['winken_links'] = winken_links

    with open('config/motor_vocabulary.json', 'w', encoding='utf-8') as f:
        json.dump(vocab, f, indent=2, ensure_ascii=False)

    # Verify
    with open('config/motor_vocabulary.json', 'r', encoding='utf-8') as f:
        check = json.load(f)
    w = check['motor_vocabulary']['words']['winken']
    wl = check['motor_vocabulary']['words']['winken_links']
    print(f"\nJSON OK — motor_vocabulary.json aktualisiert")
    print(f"  winken: {len(w['keyframes'])} KF, {w['duration_ms']}ms")
    print(f"  winken_links: {len(wl['keyframes'])} KF, {wl['duration_ms']}ms")

    # Sample arm data to verify
    for kf in w['keyframes'][:5]:
        ua = kf['bones'].get('upper_arm_R', {})
        if ua:
            hips = kf['bones'].get('hips', {})
            print(f"  t={kf['t']:.3f} upper_arm_R={ua} hips={hips}")
            break
