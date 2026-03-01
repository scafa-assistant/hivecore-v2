"""
Extrahiert confused.glb und schreibt es als 'verwirrt' in motor_vocabulary.json.

WICHTIG: confused.glb hat eine andere Ruhepose als Adams idle_natural.glb.
Deshalb berechnen wir Deltas relativ zum EIGENEN Frame 0 des Clips
(nicht relativ zum Idle). So wird nur die BEWEGUNG extrahiert.

v1.9: Hips-Translation (tx/tz) wird ebenfalls extrahiert.
Die Hueftbewegung (seitliches Schwingen) ist essentiell damit
die Bein-Rotationen natuerlich aussehen.
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
    m11 = 1 - 2*(y*y + z*z)
    m12 = 2*(x*y - w*z)
    m13 = 2*(x*z + w*y)
    m22 = 1 - 2*(x*x + z*z)
    m23 = 2*(y*z - w*x)
    m32 = 2*(y*z + w*x)
    m33 = 1 - 2*(x*x + y*y)
    ry = math.asin(max(-1.0, min(1.0, m13)))
    if abs(m13) < 0.9999999:
        rx = math.atan2(-m23, m33)
        rz = math.atan2(-m12, m11)
    else:
        rx = math.atan2(m32, m22)
        rz = 0
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))


def read_accessor_data(gltf, idx):
    acc = gltf.accessors[idx]
    bv = gltf.bufferViews[acc.bufferView]
    blob = gltf.binary_blob()
    off = (bv.byteOffset or 0) + (acc.byteOffset or 0)
    ct = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}[acc.componentType]
    nc = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[acc.type]
    fmt = f'<{acc.count * nc}{ct}'
    data = struct.unpack(fmt, blob[off:off + struct.calcsize(fmt)])
    return list(data) if nc == 1 else [data[i:i+nc] for i in range(0, len(data), nc)]


def extract_raw(path):
    gltf = GLTF2.load(path)
    if not gltf.animations:
        return {}, {}, 0
    names = {i: n.name for i, n in enumerate(gltf.nodes) if n.name}
    rotations = {}
    translations = {}
    for ch in gltf.animations[0].channels:
        node_name = names.get(ch.target.node, '')
        mn = GLB_TO_MOTOR.get(node_name)
        if not mn:
            continue
        s = gltf.animations[0].samplers[ch.sampler]
        ts = read_accessor_data(gltf, s.input)
        vals = read_accessor_data(gltf, s.output)
        if ch.target.path == 'rotation':
            rotations[mn] = list(zip(ts, vals))
        elif ch.target.path == 'translation' and len(ts) > 2:
            # Nur Bones mit animierter Translation (>2 Frames = nicht konstant)
            translations[mn] = list(zip(ts, vals))
    dur = max(t for frames in rotations.values() for t, _ in frames) if rotations else 0
    return rotations, translations, dur


def main():
    confused_path = Path(r'C:\DEV\Avatar-glb\Adam_glb+skelett\confused.glb')
    vocab_path = Path(r'C:\DEV\hivecore-v2\config\motor_vocabulary.json')

    # Confused extrahieren (Rotation + Translation)
    print(f"Extrahiere {confused_path.name}...")
    clip_rot, clip_trans, duration = extract_raw(str(confused_path))
    any_bone = next(iter(clip_rot.values()))
    clip_times = [t for t, _ in any_bone]
    n_frames = len(clip_times)
    all_bones = sorted(clip_rot.keys())
    print(f"  {n_frames} Frames, {duration:.2f}s, {len(all_bones)} Bones")
    print(f"  Translation-Bones: {sorted(clip_trans.keys())}")

    # Frame 0 als Referenz (eigene Ruhepose des Clips)
    frame0_euler = {}
    for bone in all_bones:
        q0 = clip_rot[bone][0][1]
        frame0_euler[bone] = quat_to_euler_xyz(q0)

    # Frame 0 Translation-Referenz
    frame0_trans = {}
    for bone, frames in clip_trans.items():
        frame0_trans[bone] = frames[0][1]  # (x, y, z)
        print(f"  {bone} Translation Frame 0: x={frames[0][1][0]:.2f} y={frames[0][1][1]:.2f} z={frames[0][1][2]:.2f}")

    print(f"  Referenz: Frame 0 (eigene Ruhepose des Clips)")

    # Keyframes bauen: Delta = Frame N - Frame 0
    kfs = [{"t": 0.0, "bones": {}}]  # Start = keine Bewegung

    for frame_idx, clip_t in enumerate(clip_times):
        t_norm = clip_t / duration if duration > 0 else 0
        t_kf = round(0.03 + t_norm * 0.94, 4)

        bones = {}
        for bone in all_bones:
            clip_q = clip_rot[bone][frame_idx][1]
            clip_euler = quat_to_euler_xyz(clip_q)
            ref_euler = frame0_euler[bone]

            vals = {}
            for i, ax in enumerate(['rx', 'ry', 'rz']):
                d = round(clip_euler[i] - ref_euler[i], 1)
                if abs(d) >= 0.5:
                    vals[ax] = d

            # Translation-Deltas (nur fuer Bones mit animierter Translation)
            if bone in clip_trans and frame_idx < len(clip_trans[bone]):
                pos = clip_trans[bone][frame_idx][1]
                ref_pos = frame0_trans[bone]
                for i, ax in enumerate(['tx', 'ty', 'tz']):
                    d = round(pos[i] - ref_pos[i], 2)
                    if abs(d) >= 0.1:  # 0.1 Einheiten Threshold
                        vals[ax] = d

            if vals:
                bones[bone] = vals

        kfs.append({"t": t_kf, "bones": bones})

    kfs.append({"t": 1.0, "bones": {}})  # Ende = zurueck zur Ausgangspose

    print(f"  -> {len(kfs)} Motor-Keyframes")

    # Statistik: welche Bones bewegen sich am meisten?
    max_deltas = {}
    for kf in kfs:
        for bone, vals in kf.get('bones', {}).items():
            for ax, v in vals.items():
                key = f'{bone}.{ax}'
                max_deltas[key] = max(max_deltas.get(key, 0), abs(v))
    top = sorted(max_deltas.items(), key=lambda x: -x[1])[:10]
    print(f"\n  Top 10 Bewegungen:")
    for k, v in top:
        print(f"    {k}: {v:.1f}°")

    # Vocabulary laden und updaten
    print(f"\nLade {vocab_path}...")
    with open(vocab_path, 'r', encoding='utf-8') as f:
        vocab = json.load(f)

    words = vocab['motor_vocabulary']['words']

    words['verwirrt'] = {
        "id": "MOT_CONFUSED",
        "category": "expression",
        "type": "sequence",
        "duration_ms": int(duration * 1000),
        "_fix": "v1.9: Rotation + Hips-Translation (tx/tz) fuer natuerliches Hueftschwingen",
        "_source": "confused.glb (Confused_Scratch Animation)",
        "keyframes": kfs,
        "easing": "ease_in_out",
        "loopable": False,
        "blendable": False,
        "glb_fallback": None,
    }

    vocab['motor_vocabulary']['version'] = '1.9'

    with open(vocab_path, 'w', encoding='utf-8') as f:
        json.dump(vocab, f, indent=2, ensure_ascii=False)

    print(f"\n verwirrt -> v1.9")
    print(f"  {int(duration * 1000)}ms, {len(kfs)} Frames, {len(all_bones)} Bones")

    with open(vocab_path, 'r', encoding='utf-8') as f:
        json.load(f)
    print("  JSON OK")

    size = vocab_path.stat().st_size
    print(f"  Dateigroesse: {size/1024:.0f} KB")


if __name__ == '__main__':
    main()
