"""
GLB Animation Keyframe Extractor
Extrahiert alle Bone-Rotationen aus einem GLB-Clip und berechnet
Deltas relativ zur Idle-Animation (fuer Motor-Vocabulary).

Ausgabe: JSON-kompatible Keyframes mit allen Bones die sich bewegen.
"""

import json
import struct
import math
import sys
from pathlib import Path
import numpy as np
from pygltflib import GLTF2

# Bone-Mapping: GLB-Name -> Motor-Vocabulary-Name
GLB_TO_MOTOR = {
    'Hips': 'hips',
    'Spine02': 'spine_0',
    'Spine01': 'spine_1',
    'Spine': 'spine_2',
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
    # Three.js uses intrinsic XYZ (same as extrinsic ZYX)
    # Roll (X)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    rx = math.atan2(sinr_cosp, cosr_cosp)
    # Pitch (Y)
    sinp = 2 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))
    ry = math.asin(sinp)
    # Yaw (Z)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    rz = math.atan2(siny_cosp, cosy_cosp)
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))


def read_accessor_data(gltf, accessor_index):
    """Liest Accessor-Daten aus dem GLB-Binary-Buffer."""
    accessor = gltf.accessors[accessor_index]
    buffer_view = gltf.bufferViews[accessor.bufferView]

    # Binary blob
    blob = gltf.binary_blob()

    offset = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
    count = accessor.count

    # Component type
    comp_types = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}
    comp_fmt = comp_types.get(accessor.componentType, 'f')

    # Number of components per element
    type_counts = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
    n_comp = type_counts.get(accessor.type, 1)

    fmt = f'<{count * n_comp}{comp_fmt}'
    size = struct.calcsize(fmt)
    data = struct.unpack(fmt, blob[offset:offset + size])

    if n_comp == 1:
        return list(data)
    else:
        return [data[i:i+n_comp] for i in range(0, len(data), n_comp)]


def extract_animations(glb_path):
    """Extrahiert alle Animations-Keyframes aus einer GLB-Datei.

    Returns: {bone_name: [(time, (rx, ry, rz)), ...], ...}
    """
    gltf = GLTF2.load(glb_path)

    if not gltf.animations:
        print(f"  Keine Animationen in {glb_path}")
        return {}

    # Node-Index -> Name mapping
    node_names = {}
    for i, node in enumerate(gltf.nodes):
        if node.name:
            node_names[i] = node.name

    anim = gltf.animations[0]  # Erste Animation
    print(f"  Animation: '{anim.name}', {len(anim.channels)} Channels")

    result = {}

    for channel in anim.channels:
        if channel.target.path != 'rotation':
            continue  # Nur Rotationen

        node_idx = channel.target.node
        node_name = node_names.get(node_idx, f'node_{node_idx}')

        # Motor-Name
        motor_name = GLB_TO_MOTOR.get(node_name)
        if not motor_name:
            continue  # Skip Bones die nicht im Motor-System sind

        sampler = anim.samplers[channel.sampler]

        # Zeitpunkte
        times = read_accessor_data(gltf, sampler.input)
        # Quaternions (x, y, z, w)
        quats = read_accessor_data(gltf, sampler.output)

        # Zu Euler konvertieren
        bone_frames = []
        for t, q in zip(times, quats):
            euler = quat_to_euler_xyz(q)
            bone_frames.append((t, euler))

        result[motor_name] = bone_frames

    return result


def compute_deltas(anim_data, idle_data):
    """Berechnet Deltas: anim - idle fuer jeden Bone.

    Fuer Idle wird der Mittelwert ueber alle Frames genommen (Idle ist zyklisch).
    """
    # Idle-Durchschnitt pro Bone
    idle_avg = {}
    for bone, frames in idle_data.items():
        rxs = [f[1][0] for f in frames]
        rys = [f[1][1] for f in frames]
        rzs = [f[1][2] for f in frames]
        idle_avg[bone] = (np.mean(rxs), np.mean(rys), np.mean(rzs))

    # Deltas berechnen
    result = {}
    for bone, frames in anim_data.items():
        idle_rot = idle_avg.get(bone, (0, 0, 0))
        delta_frames = []
        for t, (rx, ry, rz) in frames:
            dx = rx - idle_rot[0]
            dy = ry - idle_rot[1]
            dz = rz - idle_rot[2]
            delta_frames.append((t, (dx, dy, dz)))
        result[bone] = delta_frames

    return result


def find_significant_keyframes(delta_data, threshold=1.0, max_keyframes=12):
    """Findet die wichtigsten Zeitpunkte und gibt Motor-Vocabulary Keyframes zurueck.

    threshold: Mindest-Delta in Grad um als "bewegt" zu gelten.
    """
    if not delta_data:
        return []

    # Alle Zeitpunkte sammeln
    all_times = set()
    for bone, frames in delta_data.items():
        for t, _ in frames:
            all_times.add(round(t, 4))
    all_times = sorted(all_times)

    if not all_times:
        return []

    total_duration = all_times[-1]
    print(f"  Clip-Laenge: {total_duration:.2f}s, {len(all_times)} Frames total")

    # Fuer jeden Zeitpunkt: Interpoliere alle Bones
    def interpolate_bone_at(bone_frames, t):
        """Interpoliert Bone-Rotation zum Zeitpunkt t."""
        if not bone_frames:
            return (0, 0, 0)
        if t <= bone_frames[0][0]:
            return bone_frames[0][1]
        if t >= bone_frames[-1][0]:
            return bone_frames[-1][1]

        for i in range(len(bone_frames) - 1):
            t0, rot0 = bone_frames[i]
            t1, rot1 = bone_frames[i + 1]
            if t0 <= t <= t1:
                frac = (t - t0) / (t1 - t0) if t1 > t0 else 0
                return (
                    rot0[0] + (rot1[0] - rot0[0]) * frac,
                    rot0[1] + (rot1[1] - rot0[1]) * frac,
                    rot0[2] + (rot1[2] - rot0[2]) * frac,
                )
        return bone_frames[-1][1]

    # Subsample: Gleichmaessig verteilte Zeitpunkte + Start/Ende
    n_samples = min(max_keyframes, len(all_times))
    sample_times = [0.0]
    for i in range(1, n_samples - 1):
        sample_times.append(total_duration * i / (n_samples - 1))
    sample_times.append(total_duration)
    # Deduplizieren und sortieren
    sample_times = sorted(set([round(t, 4) for t in sample_times]))

    # Keyframes bauen
    keyframes = []
    for t in sample_times:
        t_normalized = round(t / total_duration, 3) if total_duration > 0 else 0
        bones = {}

        for bone_name, bone_frames in delta_data.items():
            rot = interpolate_bone_at(bone_frames, t)
            rx, ry, rz = round(rot[0], 1), round(rot[1], 1), round(rot[2], 1)

            # Nur signifikante Deltas
            bone_vals = {}
            if abs(rx) >= threshold:
                bone_vals['rx'] = rx
            if abs(ry) >= threshold:
                bone_vals['ry'] = ry
            if abs(rz) >= threshold:
                bone_vals['rz'] = rz

            if bone_vals:
                bones[bone_name] = bone_vals

        keyframes.append({
            't': t_normalized,
            't_seconds': round(t, 3),
            'bones': bones,
        })

    return keyframes


def main():
    base = Path(r'C:\DEV\EgonsDash\assets\3d\adam')

    clips_to_extract = ['waving_right', 'waving_left', 'head_shake']
    idle_path = base / 'idle_natural.glb'

    print("=" * 60)
    print("GLB Keyframe Extractor — Motor-Vocabulary")
    print("=" * 60)

    # Idle extrahieren
    print(f"\n--- Idle (Basis-Pose) ---")
    print(f"  Datei: {idle_path}")
    idle_data = extract_animations(str(idle_path))
    print(f"  Bones: {len(idle_data)}")

    for clip_name in clips_to_extract:
        clip_path = base / f'{clip_name}.glb'
        if not clip_path.exists():
            print(f"\n--- {clip_name} --- NICHT GEFUNDEN")
            continue

        print(f"\n{'=' * 60}")
        print(f"--- {clip_name} ---")
        print(f"  Datei: {clip_path}")

        anim_data = extract_animations(str(clip_path))
        print(f"  Bones mit Rotation: {len(anim_data)}")

        # Deltas berechnen
        deltas = compute_deltas(anim_data, idle_data)

        # Keyframes extrahieren
        keyframes = find_significant_keyframes(deltas, threshold=1.0, max_keyframes=12)

        # Ausgabe
        print(f"\n  Motor-Vocabulary Keyframes ({len(keyframes)} Frames):")
        print(f"  " + "-" * 50)

        for kf in keyframes:
            bone_str = ", ".join([
                f'"{b}": {json.dumps(v)}'
                for b, v in sorted(kf['bones'].items())
            ])
            print(f'  t={kf["t"]:.3f} ({kf["t_seconds"]:.2f}s): {{ {bone_str} }}')

        # JSON-Ausgabe
        print(f"\n  JSON fuer motor_vocabulary.json:")
        clean_kfs = [{"t": kf["t"], "bones": kf["bones"]} for kf in keyframes]
        print(json.dumps(clean_kfs, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
