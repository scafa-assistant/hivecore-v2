"""Extrahiert das komplette Schlaf-System:
1. sleeping.glb → Schlafpose (Durchschnitt ueber alle Frames)
2. Stand_Up.glb → Aufsteh-Keyframes
3. Erzeugt: hinlegen_schlafen (Stand_Up invertiert + sleeping-Pose halten)
4. Erzeugt: aufstehen (Stand_Up normal + explizite Null-Werte am Ende)

Idle-relative Deltas (korrekte Methode via pygltflib).
"""
import json
import struct
import math
import copy
import numpy as np
from pygltflib import GLTF2

GLB_TO_MOTOR = {
    'Hips': 'hips',
    'Spine02': 'spine2', 'Spine01': 'spine1', 'Spine': 'spine',
    'neck': 'neck', 'Head': 'head',
    'LeftShoulder': 'shoulder_L', 'RightShoulder': 'shoulder_R',
    'LeftArm': 'upper_arm_L', 'RightArm': 'upper_arm_R',
    'LeftForeArm': 'lower_arm_L', 'RightForeArm': 'lower_arm_R',
    'LeftHand': 'hand_L', 'RightHand': 'hand_R',
    'LeftUpLeg': 'upper_leg_L', 'RightUpLeg': 'upper_leg_R',
    'LeftLeg': 'lower_leg_L', 'RightLeg': 'lower_leg_R',
    'LeftFoot': 'foot_L', 'RightFoot': 'foot_R',
}


def quat_to_euler_xyz(q):
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
    gltf = GLTF2.load(glb_path)
    if not gltf.animations:
        return {}
    node_names = {i: n.name for i, n in enumerate(gltf.nodes) if n.name}
    anim = gltf.animations[0]
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
        if path_type == 'translation' and motor_name != 'hips':
            continue
        sampler = anim.samplers[channel.sampler]
        times = read_accessor_data(gltf, sampler.input)
        values = read_accessor_data(gltf, sampler.output)
        if motor_name not in result:
            result[motor_name] = {}
        if path_type == 'rotation':
            result[motor_name]['rotation'] = [(t, quat_to_euler_xyz(q)) for t, q in zip(times, values)]
        elif path_type == 'translation':
            result[motor_name]['translation'] = [(t, v) for t, v in zip(times, values)]
    return result


def compute_idle_avg(idle_data):
    """Berechnet Idle-Durchschnitt fuer Rotation und Translation."""
    rot_avg = {}
    for bone, data in idle_data.items():
        if 'rotation' in data:
            frames = data['rotation']
            rot_avg[bone] = (
                np.mean([f[1][0] for f in frames]),
                np.mean([f[1][1] for f in frames]),
                np.mean([f[1][2] for f in frames]),
            )
    trans_avg = None
    if 'hips' in idle_data and 'translation' in idle_data['hips']:
        frames = idle_data['hips']['translation']
        trans_avg = (
            np.mean([f[1][0] for f in frames]),
            np.mean([f[1][1] for f in frames]),
            np.mean([f[1][2] for f in frames]),
        )
    return rot_avg, trans_avg


def compute_sleeping_pose(sleep_data, idle_rot_avg, idle_trans_avg, threshold_rot=0.5, threshold_trans=0.1):
    """Berechnet die durchschnittliche Schlafpose als idle-relative Deltas."""
    pose = {}
    for bone, data in sleep_data.items():
        vals = {}
        if 'rotation' in data:
            frames = data['rotation']
            avg = (np.mean([f[1][0] for f in frames]),
                   np.mean([f[1][1] for f in frames]),
                   np.mean([f[1][2] for f in frames]))
            idle = idle_rot_avg.get(bone, (0, 0, 0))
            drx = round(avg[0] - idle[0], 1)
            dry = round(avg[1] - idle[1], 1)
            drz = round(avg[2] - idle[2], 1)
            if abs(drx) >= threshold_rot: vals['rx'] = drx
            if abs(dry) >= threshold_rot: vals['ry'] = dry
            if abs(drz) >= threshold_rot: vals['rz'] = drz

        if bone == 'hips' and 'translation' in data and idle_trans_avg:
            frames = data['translation']
            avg = (np.mean([f[1][0] for f in frames]),
                   np.mean([f[1][1] for f in frames]),
                   np.mean([f[1][2] for f in frames]))
            dtx = round(avg[0] - idle_trans_avg[0], 2)
            dty = round(avg[1] - idle_trans_avg[1], 2)
            dtz = round(avg[2] - idle_trans_avg[2], 2)
            if abs(dtx) >= threshold_trans: vals['tx'] = dtx
            if abs(dty) >= threshold_trans: vals['ty'] = dty
            if abs(dtz) >= threshold_trans: vals['tz'] = dtz

        if vals:
            pose[bone] = vals
    return pose


def build_all_keyframes(anim_data, idle_rot_avg, idle_trans_avg, threshold_rot=0.5, threshold_trans=0.1):
    """Baut Keyframes aus Allen Frames mit idle-relativen Deltas."""
    all_times = set()
    for bone, data in anim_data.items():
        if 'rotation' in data:
            for t, _ in data['rotation']:
                all_times.add(round(t, 4))
    all_times = sorted(all_times)
    if not all_times:
        return [], 0

    total_duration = all_times[-1]

    def interpolate_at(frames, t):
        if not frames: return None
        if t <= frames[0][0]: return frames[0][1]
        if t >= frames[-1][0]: return frames[-1][1]
        for i in range(len(frames) - 1):
            t0, v0 = frames[i]
            t1, v1 = frames[i + 1]
            if t0 <= t <= t1:
                frac = (t - t0) / (t1 - t0) if t1 > t0 else 0
                return tuple(v0[j] + (v1[j] - v0[j]) * frac for j in range(len(v0)))
        return frames[-1][1]

    keyframes = []
    for t in all_times:
        t_norm = round(t / total_duration, 4) if total_duration > 0 else 0
        bones = {}
        for bone, data in anim_data.items():
            vals = {}
            if 'rotation' in data:
                rot = interpolate_at(data['rotation'], t)
                if rot:
                    idle = idle_rot_avg.get(bone, (0, 0, 0))
                    rx, ry, rz = round(rot[0]-idle[0], 1), round(rot[1]-idle[1], 1), round(rot[2]-idle[2], 1)
                    if abs(rx) >= threshold_rot: vals['rx'] = rx
                    if abs(ry) >= threshold_rot: vals['ry'] = ry
                    if abs(rz) >= threshold_rot: vals['rz'] = rz
            if bone == 'hips' and 'translation' in data and idle_trans_avg:
                trans = interpolate_at(data['translation'], t)
                if trans:
                    tx = round(trans[0]-idle_trans_avg[0], 2)
                    ty = round(trans[1]-idle_trans_avg[1], 2)
                    tz = round(trans[2]-idle_trans_avg[2], 2)
                    if abs(tx) >= threshold_trans: vals['tx'] = tx
                    if abs(ty) >= threshold_trans: vals['ty'] = ty
                    if abs(tz) >= threshold_trans: vals['tz'] = tz
            if vals:
                bones[bone] = vals
        if bones:
            keyframes.append({'t': t_norm, 'bones': bones})
    return keyframes, int(total_duration * 1000)


def make_zero_frame(keyframes):
    """Erzeugt einen Keyframe mit expliziten Nullen fuer alle Bones/Achsen."""
    all_axes = {}
    for kf in keyframes:
        for bone, vals in kf['bones'].items():
            if bone not in all_axes:
                all_axes[bone] = set()
            all_axes[bone].update(vals.keys())
    zero_bones = {}
    for bone, axes in all_axes.items():
        zero_bones[bone] = {ax: 0.0 for ax in sorted(axes)}
    return zero_bones


if __name__ == '__main__':
    idle_path = r'C:\DEV\EgonsDash\assets\3d\adam\idle_natural.glb'
    standup_path = r'C:\DEV\Avatar-glb\Adam_glb+skelett\Stand_Up.glb'
    sleeping_path = r'C:\DEV\Avatar-glb\Adam_glb+skelett\sleeping.glb'

    # === Idle Referenz ===
    print("=== Idle (Referenz) ===")
    idle_data = extract_animations(idle_path, include_translation=True)
    idle_rot_avg, idle_trans_avg = compute_idle_avg(idle_data)
    print(f"  Bones: {len(idle_data)}, Idle Hips avg Y: {idle_trans_avg[1]:.2f}")

    # === Sleeping Pose ===
    print("\n=== Sleeping Pose ===")
    sleep_data = extract_animations(sleeping_path, include_translation=True)
    sleeping_pose = compute_sleeping_pose(sleep_data, idle_rot_avg, idle_trans_avg)
    print(f"  Bones in Pose: {len(sleeping_pose)}")
    print(f"  Hips: {sleeping_pose.get('hips', {})}")
    print(f"  Head: {sleeping_pose.get('head', {})}")

    # === Stand_Up Keyframes ===
    print("\n=== Stand_Up ===")
    standup_data = extract_animations(standup_path, include_translation=True)
    keyframes, duration_ms = build_all_keyframes(standup_data, idle_rot_avg, idle_trans_avg)
    print(f"  Keyframes: {len(keyframes)}, Duration: {duration_ms}ms")
    hips_ty = [kf['bones'].get('hips', {}).get('ty', 0) for kf in keyframes]
    print(f"  Hips TY: {min(hips_ty):.2f} to {max(hips_ty):.2f}")

    # === Zero-Frame (explizite Nullen) ===
    zero_bones = make_zero_frame(keyframes)
    print(f"\n  Zero-Frame Bones: {len(zero_bones)}")

    # === AUFSTEHEN ===
    print("\n=== Erzeuge aufstehen ===")
    aufstehen_kfs = list(keyframes)
    # Letzter Frame: explizite Nullen statt leer
    aufstehen_kfs.append({'t': 1.0, 'bones': zero_bones})
    aufstehen = {
        'id': 'MOT_STAND_UP',
        'category': 'transition',
        'type': 'sequence',
        'duration_ms': duration_ms + 500,
        'keyframes': aufstehen_kfs,
        'easing': 'ease_out',
        'loopable': False,
        'blendable': False,
        'glb_fallback': None,
    }
    print(f"  aufstehen: {len(aufstehen_kfs)} KF, {aufstehen['duration_ms']}ms")

    # === HINLEGEN_SCHLAFEN ===
    print("\n=== Erzeuge hinlegen_schlafen ===")
    total_dur = 600000  # 10 Minuten
    lie_down_ms = duration_ms
    lie_down_ratio = lie_down_ms / total_dur

    # Invertiere Keyframes
    reversed_kfs = list(reversed(keyframes))
    n = len(reversed_kfs)
    remapped_kfs = []
    for i, kf in enumerate(reversed_kfs):
        new_t = round(lie_down_ratio * i / max(n - 1, 1), 6)
        remapped_kfs.append({'t': new_t, 'bones': copy.deepcopy(kf['bones'])})

    # Uebergang zur Schlafpose: kurz nach dem Hinlegen
    transition_t = round(lie_down_ratio * 1.5, 6)  # 50% laenger als Hinlegen
    remapped_kfs.append({'t': transition_t, 'bones': copy.deepcopy(sleeping_pose)})

    # Halte-Keyframe: Schlafpose bis zum Ende
    remapped_kfs.append({'t': 1.0, 'bones': copy.deepcopy(sleeping_pose)})

    hinlegen = {
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
    print(f"  hinlegen_schlafen: {len(remapped_kfs)} KF, {total_dur}ms")
    ts = [kf['t'] for kf in remapped_kfs]
    print(f"    Lie-down: t=0 to t={ts[n-1]:.6f} ({ts[n-1]*total_dur:.0f}ms)")
    print(f"    Transition to sleep: t={transition_t:.6f} ({transition_t*total_dur:.0f}ms)")
    print(f"    Sleep hold: t={transition_t:.6f} to t=1.0")
    print(f"    Sleeping pose hips: {sleeping_pose.get('hips', {})}")

    # === In motor_vocabulary.json einsetzen ===
    with open('config/motor_vocabulary.json', 'r', encoding='utf-8') as f:
        vocab = json.load(f)

    words = vocab['motor_vocabulary']['words']
    words['hinlegen_schlafen'] = hinlegen
    words['aufstehen'] = aufstehen

    with open('config/motor_vocabulary.json', 'w', encoding='utf-8') as f:
        json.dump(vocab, f, indent=2, ensure_ascii=False)

    with open('config/motor_vocabulary.json', 'r', encoding='utf-8') as f:
        json.load(f)
    print("\nJSON OK")
