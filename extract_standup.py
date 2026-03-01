"""Extrahiert Stand_Up.glb als Motor-Keyframes.
Deltas relativ zur Idle-Animation (korrekte Referenz fuer additive Motor-Offsets).
Erzeugt: aufstehen (normal) + hinlegen_schlafen (invertiert + Haltepose).

Basiert auf extract_glb_keyframes.py (idle-relativ, pygltflib).
"""
import json
import struct
import math
import numpy as np
from pygltflib import GLTF2

# Bone-Mapping: GLB-Name → Motor-Name (korrekte Namen)
GLB_TO_MOTOR = {
    'Hips': 'hips',
    'Spine02': 'spine2',
    'Spine01': 'spine1',
    'Spine': 'spine',
    'neck': 'neck',
    'Head': 'head',
    'LeftShoulder': 'shoulder_L',
    'LeftArm': 'upper_arm_L',
    'LeftForeArm': 'lower_arm_L',
    'LeftHand': 'hand_L',
    'RightShoulder': 'shoulder_R',
    'RightArm': 'upper_arm_R',
    'RightForeArm': 'lower_arm_R',
    'RightHand': 'hand_R',
    'LeftUpLeg': 'upper_leg_L',
    'LeftLeg': 'lower_leg_L',
    'LeftFoot': 'foot_L',
    'RightUpLeg': 'upper_leg_R',
    'RightLeg': 'lower_leg_R',
    'RightFoot': 'foot_R',
}


def quat_to_euler_xyz(q):
    """Quaternion (x,y,z,w) -> Euler XYZ in Grad (Three.js Konvention)."""
    x, y, z, w = q
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    rx = math.atan2(sinr_cosp, cosr_cosp)
    sinp = 2 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))
    ry = math.asin(sinp)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    rz = math.atan2(siny_cosp, cosy_cosp)
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))


def read_accessor_data(gltf, accessor_index):
    """Liest Accessor-Daten aus dem GLB-Binary-Buffer."""
    accessor = gltf.accessors[accessor_index]
    buffer_view = gltf.bufferViews[accessor.bufferView]
    blob = gltf.binary_blob()
    offset = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
    count = accessor.count
    comp_types = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}
    comp_fmt = comp_types.get(accessor.componentType, 'f')
    type_counts = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
    n_comp = type_counts.get(accessor.type, 1)
    fmt = f'<{count * n_comp}{comp_fmt}'
    data = struct.unpack(fmt, blob[offset:offset + struct.calcsize(fmt)])
    if n_comp == 1:
        return list(data)
    else:
        return [data[i:i+n_comp] for i in range(0, len(data), n_comp)]


def extract_animations(glb_path, include_translation=False):
    """Extrahiert Rotationen (und optional Translation) aus GLB.
    Returns: {bone_name: {'rotation': [(t, (rx,ry,rz))], 'translation': [(t, (x,y,z))]}}
    """
    gltf = GLTF2.load(glb_path)
    if not gltf.animations:
        return {}

    node_names = {i: n.name for i, n in enumerate(gltf.nodes) if n.name}
    anim = gltf.animations[0]
    print(f"  Animation: '{anim.name}', {len(anim.channels)} Channels")

    result = {}
    for channel in anim.channels:
        path_type = channel.target.path
        if path_type == 'scale':
            continue
        if path_type == 'translation' and not include_translation:
            continue

        node_idx = channel.target.node
        node_name = node_names.get(node_idx, f'node_{node_idx}')
        motor_name = GLB_TO_MOTOR.get(node_name)
        if not motor_name:
            continue

        # Nur Hips-Translation (andere Bones haben statische Translation)
        if path_type == 'translation' and motor_name != 'hips':
            continue

        sampler = anim.samplers[channel.sampler]
        times = read_accessor_data(gltf, sampler.input)
        values = read_accessor_data(gltf, sampler.output)

        if motor_name not in result:
            result[motor_name] = {}

        if path_type == 'rotation':
            frames = [(t, quat_to_euler_xyz(q)) for t, q in zip(times, values)]
            result[motor_name]['rotation'] = frames
        elif path_type == 'translation':
            frames = [(t, v) for t, v in zip(times, values)]
            result[motor_name]['translation'] = frames

    return result


def compute_deltas(anim_data, idle_data):
    """Berechnet Deltas relativ zum Idle-Durchschnitt."""
    # Idle-Durchschnitt pro Bone (Rotation)
    idle_rot_avg = {}
    for bone, data in idle_data.items():
        if 'rotation' in data:
            frames = data['rotation']
            idle_rot_avg[bone] = (
                np.mean([f[1][0] for f in frames]),
                np.mean([f[1][1] for f in frames]),
                np.mean([f[1][2] for f in frames]),
            )

    # Idle-Durchschnitt Hips-Translation
    idle_trans_avg = None
    if 'hips' in idle_data and 'translation' in idle_data['hips']:
        frames = idle_data['hips']['translation']
        idle_trans_avg = (
            np.mean([f[1][0] for f in frames]),
            np.mean([f[1][1] for f in frames]),
            np.mean([f[1][2] for f in frames]),
        )

    # Deltas berechnen
    result = {}
    for bone, data in anim_data.items():
        result[bone] = {}

        if 'rotation' in data:
            idle_rot = idle_rot_avg.get(bone, (0, 0, 0))
            delta_frames = []
            for t, (rx, ry, rz) in data['rotation']:
                delta_frames.append((t, (
                    rx - idle_rot[0],
                    ry - idle_rot[1],
                    rz - idle_rot[2],
                )))
            result[bone]['rotation'] = delta_frames

        if 'translation' in data and idle_trans_avg:
            delta_frames = []
            for t, (x, y, z) in data['translation']:
                delta_frames.append((t, (
                    x - idle_trans_avg[0],
                    y - idle_trans_avg[1],
                    z - idle_trans_avg[2],
                )))
            result[bone]['translation'] = delta_frames

    return result


def build_keyframes(delta_data, threshold_rot=0.5, threshold_trans=0.1):
    """Baut Motor-Vocabulary Keyframes aus Allen Frames (kein Subsampling)."""
    # Alle Zeitpunkte sammeln (aus Rotation)
    all_times = set()
    for bone, data in delta_data.items():
        if 'rotation' in data:
            for t, _ in data['rotation']:
                all_times.add(round(t, 4))
    all_times = sorted(all_times)

    if not all_times:
        return [], 0

    total_duration = all_times[-1]

    def interpolate_at(frames, t):
        if not frames:
            return None
        if t <= frames[0][0]:
            return frames[0][1]
        if t >= frames[-1][0]:
            return frames[-1][1]
        for i in range(len(frames) - 1):
            t0, v0 = frames[i]
            t1, v1 = frames[i + 1]
            if t0 <= t <= t1:
                frac = (t - t0) / (t1 - t0) if t1 > t0 else 0
                if len(v0) == 3:
                    return (
                        v0[0] + (v1[0] - v0[0]) * frac,
                        v0[1] + (v1[1] - v0[1]) * frac,
                        v0[2] + (v1[2] - v0[2]) * frac,
                    )
        return frames[-1][1]

    keyframes = []
    for t in all_times:
        t_norm = round(t / total_duration, 4) if total_duration > 0 else 0
        bones = {}

        for bone, data in delta_data.items():
            vals = {}

            # Rotation
            if 'rotation' in data:
                rot = interpolate_at(data['rotation'], t)
                if rot:
                    rx, ry, rz = round(rot[0], 1), round(rot[1], 1), round(rot[2], 1)
                    if abs(rx) >= threshold_rot:
                        vals['rx'] = rx
                    if abs(ry) >= threshold_rot:
                        vals['ry'] = ry
                    if abs(rz) >= threshold_rot:
                        vals['rz'] = rz

            # Translation (nur Hips)
            if bone == 'hips' and 'translation' in data:
                trans = interpolate_at(data['translation'], t)
                if trans:
                    tx, ty, tz = round(trans[0], 2), round(trans[1], 2), round(trans[2], 2)
                    if abs(tx) >= threshold_trans:
                        vals['tx'] = tx
                    if abs(ty) >= threshold_trans:
                        vals['ty'] = ty
                    if abs(tz) >= threshold_trans:
                        vals['tz'] = tz

            if vals:
                bones[bone] = vals

        if bones:
            keyframes.append({'t': t_norm, 'bones': bones})

    return keyframes, int(total_duration * 1000)


def make_aufstehen(keyframes, duration_ms):
    """Aufstehen: GLB normal (liegend → stehend), dann fade zu idle."""
    kfs = list(keyframes)
    # Letzter Keyframe: leere Bones → fade zu REST_POSE
    kfs.append({'t': 1.0, 'bones': {}})
    return {
        'id': 'MOT_STAND_UP',
        'category': 'transition',
        'type': 'sequence',
        'duration_ms': duration_ms + 200,  # Kleiner Puffer
        'keyframes': kfs,
        'easing': 'ease_out',
        'loopable': False,
        'blendable': False,
        'glb_fallback': None,
    }


def make_hinlegen_schlafen(keyframes, duration_ms):
    """Hinlegen: GLB invertiert (stehend → liegend), dann Pose halten.
    Duration 600000ms (10 Min). Lie-down belegt ~t=0 bis t=0.005.
    """
    total_dur = 600000  # 10 Minuten
    lie_down_ratio = duration_ms / total_dur  # ~0.0047

    # Invertiere Keyframes (letzter Frame → erster Frame)
    reversed_kfs = list(reversed(keyframes))

    # Re-normalisiere t: 0 bis lie_down_ratio
    n = len(reversed_kfs)
    remapped_kfs = []
    for i, kf in enumerate(reversed_kfs):
        new_t = round(lie_down_ratio * i / max(n - 1, 1), 6)
        remapped_kfs.append({'t': new_t, 'bones': kf['bones']})

    # Haltepose: letzter Frame der Hinlege-Bewegung = erster Frame der GLB (liegend)
    lying_pose = remapped_kfs[-1]['bones']

    # Halte-Keyframe bei t=1.0
    remapped_kfs.append({'t': 1.0, 'bones': lying_pose})

    return {
        'id': 'MOT_LIE_DOWN_SLEEP',
        'category': 'transition',
        'type': 'sequence',
        'duration_ms': total_dur,
        'keyframes': remapped_kfs,
        'easing': 'ease_in_out',
        'loopable': False,
        'blendable': False,
        'glb_fallback': None,
    }


if __name__ == '__main__':
    idle_path = r'C:\DEV\EgonsDash\assets\3d\adam\idle_natural.glb'
    standup_path = r'C:\DEV\Avatar-glb\Adam_glb+skelett\Stand_Up.glb'

    print("=== Extrahiere Idle (Referenz) ===")
    idle_data = extract_animations(idle_path, include_translation=True)
    print(f"  Bones: {len(idle_data)}")
    if 'hips' in idle_data and 'translation' in idle_data['hips']:
        frames = idle_data['hips']['translation']
        avg_y = np.mean([f[1][1] for f in frames])
        print(f"  Idle Hips avg Y: {avg_y:.2f}")

    print("\n=== Extrahiere Stand_Up ===")
    standup_data = extract_animations(standup_path, include_translation=True)
    print(f"  Bones: {len(standup_data)}")
    if 'hips' in standup_data and 'translation' in standup_data['hips']:
        frames = standup_data['hips']['translation']
        print(f"  Stand_Up Hips Y: {frames[0][1][1]:.2f} (liegend) -> {frames[-1][1][1]:.2f} (stehend)")

    print("\n=== Berechne Deltas (relativ zu Idle) ===")
    deltas = compute_deltas(standup_data, idle_data)

    print("\n=== Baue Keyframes ===")
    keyframes, duration_ms = build_keyframes(deltas)
    print(f"  Keyframes: {len(keyframes)}, Duration: {duration_ms}ms")

    # Hips Translation Stats
    hips_ty = [kf['bones'].get('hips', {}).get('ty', 0) for kf in keyframes]
    hips_tx = [kf['bones'].get('hips', {}).get('tx', 0) for kf in keyframes]
    print(f"  Hips TY: {min(hips_ty):.2f} to {max(hips_ty):.2f}")
    print(f"  Hips TX: {min(hips_tx):.2f} to {max(hips_tx):.2f}")

    # Bones in keyframes
    all_bones = set()
    for kf in keyframes:
        all_bones.update(kf['bones'].keys())
    print(f"  Bones: {sorted(all_bones)}")

    # Sample first and last keyframe
    print(f"\n  Frame 0 (liegend): {json.dumps(keyframes[0]['bones'].get('hips', {}))}")
    print(f"  Frame -1 (stehend): {json.dumps(keyframes[-1]['bones'].get('hips', {}))}")

    print("\n=== Erzeuge Motor-Woerter ===")
    aufstehen = make_aufstehen(keyframes, duration_ms)
    print(f"  aufstehen: {len(aufstehen['keyframes'])} KF, {aufstehen['duration_ms']}ms")

    hinlegen = make_hinlegen_schlafen(keyframes, duration_ms)
    print(f"  hinlegen_schlafen: {len(hinlegen['keyframes'])} KF, {hinlegen['duration_ms']}ms")
    # Show t-distribution
    ts = [kf['t'] for kf in hinlegen['keyframes']]
    print(f"    t range: {ts[0]:.6f} to {ts[-1]:.6f}")
    print(f"    Lie-down ends at t={ts[-2]:.6f} ({ts[-2] * hinlegen['duration_ms']:.0f}ms)")

    # In motor_vocabulary.json einsetzen
    with open('config/motor_vocabulary.json', 'r', encoding='utf-8') as f:
        vocab = json.load(f)

    words = vocab['motor_vocabulary']['words']
    words['hinlegen_schlafen'] = hinlegen
    words['aufstehen'] = aufstehen

    with open('config/motor_vocabulary.json', 'w', encoding='utf-8') as f:
        json.dump(vocab, f, indent=2, ensure_ascii=False)

    # Verify
    with open('config/motor_vocabulary.json', 'r', encoding='utf-8') as f:
        json.load(f)
    print("\nJSON OK — motor_vocabulary.json aktualisiert")
