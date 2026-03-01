"""
GLB Keyframe Extractor v2 — Saubere Motor-Vocabulary Ausgabe
Extrahiert nur signifikante Bone-Rotationen (>= 5 Grad Delta).
Fuegt leere Start/End Frames hinzu fuer smooth Fade-In/Out.
"""

import json
import struct
import math
from pathlib import Path
import numpy as np
from pygltflib import GLTF2

GLB_TO_MOTOR = {
    'Hips': 'hips', 'Spine02': 'spine_0', 'Spine01': 'spine_1', 'Spine': 'spine_2',
    'neck': 'neck', 'Head': 'head',
    'LeftShoulder': 'shoulder_L', 'LeftArm': 'upper_arm_L', 'LeftForeArm': 'lower_arm_L', 'LeftHand': 'hand_L',
    'RightShoulder': 'shoulder_R', 'RightArm': 'upper_arm_R', 'RightForeArm': 'lower_arm_R', 'RightHand': 'hand_R',
    'LeftUpLeg': 'upper_leg_L', 'LeftLeg': 'lower_leg_L', 'LeftFoot': 'foot_L',
    'RightUpLeg': 'upper_leg_R', 'RightLeg': 'lower_leg_R', 'RightFoot': 'foot_R',
}

def quat_to_euler_xyz(q):
    x, y, z, w = q
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    rx = math.atan2(sinr_cosp, cosr_cosp)
    sinp = max(-1.0, min(1.0, 2 * (w * y - z * x)))
    ry = math.asin(sinp)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    rz = math.atan2(siny_cosp, cosy_cosp)
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))

def read_accessor_data(gltf, accessor_index):
    accessor = gltf.accessors[accessor_index]
    bv = gltf.bufferViews[accessor.bufferView]
    blob = gltf.binary_blob()
    offset = (bv.byteOffset or 0) + (accessor.byteOffset or 0)
    count = accessor.count
    comp_types = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}
    comp_fmt = comp_types.get(accessor.componentType, 'f')
    type_counts = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
    n_comp = type_counts.get(accessor.type, 1)
    fmt = f'<{count * n_comp}{comp_fmt}'
    data = struct.unpack(fmt, blob[offset:offset + struct.calcsize(fmt)])
    if n_comp == 1:
        return list(data)
    return [data[i:i+n_comp] for i in range(0, len(data), n_comp)]

def extract_rotations(glb_path):
    gltf = GLTF2.load(glb_path)
    if not gltf.animations:
        return {}, 0
    node_names = {i: n.name for i, n in enumerate(gltf.nodes) if n.name}
    anim = gltf.animations[0]
    result = {}
    for ch in anim.channels:
        if ch.target.path != 'rotation':
            continue
        motor_name = GLB_TO_MOTOR.get(node_names.get(ch.target.node, ''))
        if not motor_name:
            continue
        sampler = anim.samplers[ch.sampler]
        times = read_accessor_data(gltf, sampler.input)
        quats = read_accessor_data(gltf, sampler.output)
        result[motor_name] = [(t, quat_to_euler_xyz(q)) for t, q in zip(times, quats)]
    duration = max(t for frames in result.values() for t, _ in frames) if result else 0
    return result, duration

def interpolate_at(bone_frames, t):
    if not bone_frames:
        return (0, 0, 0)
    if t <= bone_frames[0][0]:
        return bone_frames[0][1]
    if t >= bone_frames[-1][0]:
        return bone_frames[-1][1]
    for i in range(len(bone_frames) - 1):
        t0, r0 = bone_frames[i]
        t1, r1 = bone_frames[i + 1]
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return (r0[0]+(r1[0]-r0[0])*f, r0[1]+(r1[1]-r0[1])*f, r0[2]+(r1[2]-r0[2])*f)
    return bone_frames[-1][1]

def main():
    base = Path(r'C:\DEV\EgonsDash\assets\3d\adam')
    THRESHOLD = 5.0  # Nur Deltas >= 5 Grad behalten

    # Idle laden
    print("Lade idle_natural.glb...")
    idle_data, _ = extract_rotations(str(base / 'idle_natural.glb'))
    idle_avg = {}
    for bone, frames in idle_data.items():
        idle_avg[bone] = (
            np.mean([f[1][0] for f in frames]),
            np.mean([f[1][1] for f in frames]),
            np.mean([f[1][2] for f in frames]),
        )

    for clip_name in ['waving_right', 'waving_left', 'head_shake']:
        clip_path = base / f'{clip_name}.glb'
        if not clip_path.exists():
            continue

        print(f"\n{'='*60}")
        print(f"  {clip_name}")
        print(f"{'='*60}")

        anim_data, duration = extract_rotations(str(clip_path))
        print(f"  Dauer: {duration:.2f}s, Bones: {len(anim_data)}")

        # 10 gleichmaessige Samples + Fade-In/Out
        n_samples = 10
        sample_times = [duration * i / (n_samples - 1) for i in range(n_samples)]

        # Finde welche Bones sich ueberhaupt bewegen (max delta > threshold)
        moving_bones = set()
        for bone in anim_data:
            idle_rot = idle_avg.get(bone, (0, 0, 0))
            max_delta = 0
            for t in sample_times:
                rot = interpolate_at(anim_data[bone], t)
                for i in range(3):
                    max_delta = max(max_delta, abs(rot[i] - idle_rot[i]))
            if max_delta >= THRESHOLD:
                moving_bones.add(bone)

        print(f"  Signifikante Bones (>={THRESHOLD}°): {sorted(moving_bones)}")

        # Keyframes bauen (mit leeren Start/End fuer Fade)
        keyframes = [{"t": 0.0, "bones": {}}]  # Fade-In Start

        for t in sample_times:
            t_norm = round(t / duration, 3) if duration > 0 else 0
            # Offset fuer Fade-In/Out Frames
            t_adjusted = round(0.05 + t_norm * 0.9, 3)  # 0.05..0.95

            bones = {}
            for bone in sorted(moving_bones):
                idle_rot = idle_avg.get(bone, (0, 0, 0))
                rot = interpolate_at(anim_data[bone], t)
                vals = {}
                dx = round(rot[0] - idle_rot[0], 1)
                dy = round(rot[1] - idle_rot[1], 1)
                dz = round(rot[2] - idle_rot[2], 1)
                if abs(dx) >= 2.0: vals['rx'] = dx
                if abs(dy) >= 2.0: vals['ry'] = dy
                if abs(dz) >= 2.0: vals['rz'] = dz
                if vals:
                    bones[bone] = vals

            keyframes.append({"t": t_adjusted, "bones": bones})

        keyframes.append({"t": 1.0, "bones": {}})  # Fade-Out End

        # Kompakte Ausgabe
        print(f"\n  Motor-Vocabulary Keyframes ({len(keyframes)} Frames, inkl. Fade):")
        print(f"  Duration: {int(duration * 1000)}ms")
        print()

        # JSON Ausgabe
        print(json.dumps(keyframes, indent=2, ensure_ascii=False))
        print()

        # Zusammenfassung
        mid_idx = len(keyframes) // 2
        mid_bones = keyframes[mid_idx]['bones']
        print(f"  Peak-Pose (t={keyframes[mid_idx]['t']}):")
        for b, v in sorted(mid_bones.items()):
            print(f"    {b}: {v}")


if __name__ == '__main__':
    main()
