"""
GLB -> Motor-Vocabulary Extractor v3
Nimmt ALLE originalen GLB-Frames (kein Sub-Sampling).
Berechnet Idle-Delta am SELBEN Zeitpunkt (nicht Durchschnitt).
Three.js-korrekte Euler-Konvertierung (XYZ intrinsic via Rotationsmatrix).
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
    """Quaternion (x,y,z,w) -> Euler XYZ in Grad.
    Exakt die Three.js Formel (Euler.setFromRotationMatrix, order='XYZ')."""
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


def slerp_quat(q0, q1, t):
    """Quaternion SLERP (Spherical Linear Interpolation)."""
    q0 = np.array(q0, dtype=np.float64)
    q1 = np.array(q1, dtype=np.float64)
    dot = np.dot(q0, q1)
    if dot < 0:
        q1 = -q1
        dot = -dot
    dot = min(dot, 1.0)
    if dot > 0.9995:
        result = q0 + t * (q1 - q0)
        return tuple(result / np.linalg.norm(result))
    theta = math.acos(dot)
    sin_theta = math.sin(theta)
    s0 = math.sin((1 - t) * theta) / sin_theta
    s1 = math.sin(t * theta) / sin_theta
    result = s0 * q0 + s1 * q1
    return tuple(result)


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
    """Extrahiert rohe Quaternions + Zeitpunkte aus GLB (KEINE Euler-Konvertierung)."""
    gltf = GLTF2.load(path)
    if not gltf.animations:
        return {}, 0
    names = {i: n.name for i, n in enumerate(gltf.nodes) if n.name}
    result = {}
    for ch in gltf.animations[0].channels:
        if ch.target.path != 'rotation':
            continue
        mn = GLB_TO_MOTOR.get(names.get(ch.target.node, ''))
        if not mn:
            continue
        s = gltf.animations[0].samplers[ch.sampler]
        ts = read_accessor_data(gltf, s.input)
        qs = read_accessor_data(gltf, s.output)
        result[mn] = list(zip(ts, qs))  # [(time, (x,y,z,w)), ...]
    dur = max(t for frames in result.values() for t, _ in frames) if result else 0
    return result, dur


def slerp_at_time(bone_frames, t):
    """Interpoliert Quaternion zum Zeitpunkt t via SLERP."""
    if not bone_frames:
        return (0, 0, 0, 1)
    if t <= bone_frames[0][0]:
        return bone_frames[0][1]
    if t >= bone_frames[-1][0]:
        return bone_frames[-1][1]
    for i in range(len(bone_frames) - 1):
        t0, q0 = bone_frames[i]
        t1, q1 = bone_frames[i + 1]
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return slerp_quat(q0, q1, f)
    return bone_frames[-1][1]


def build_keyframes_v3(clip_raw, idle_raw, duration):
    """Baut Motor-Vocabulary Keyframes aus ALLEN originalen GLB-Frames.

    Fuer jeden Frame:
    1. Clip-Quaternion -> Euler (Three.js Formel)
    2. Idle-Quaternion am SELBEN Zeitpunkt via SLERP -> Euler
    3. Delta = Clip-Euler - Idle-Euler
    """
    # Alle Zeitpunkte aus dem Clip sammeln (alle Bones haben gleiche Zeiten)
    any_bone = next(iter(clip_raw.values()))
    clip_times = [t for t, _ in any_bone]
    n_frames = len(clip_times)

    # Alle Bones die im Clip vorkommen
    all_bones = sorted(clip_raw.keys())

    # Keyframes bauen: Start-Fade + alle Original-Frames + End-Fade
    kfs = [{"t": 0.0, "bones": {}}]  # Fade-In

    for frame_idx, clip_t in enumerate(clip_times):
        t_norm = clip_t / duration if duration > 0 else 0
        # Keyframe-Zeit: 0.03..0.97 (3% Fade-In/Out Puffer)
        t_kf = round(0.03 + t_norm * 0.94, 4)

        bones = {}
        for bone in all_bones:
            # Clip-Quaternion an diesem Frame
            clip_q = clip_raw[bone][frame_idx][1] if frame_idx < len(clip_raw[bone]) else clip_raw[bone][-1][1]
            clip_euler = quat_to_euler_xyz(clip_q)

            # Idle-Quaternion am SELBEN Zeitpunkt (via SLERP)
            idle_q = slerp_at_time(idle_raw.get(bone, []), clip_t)
            idle_euler = quat_to_euler_xyz(idle_q)

            # Delta
            vals = {}
            for i, ax in enumerate(['rx', 'ry', 'rz']):
                d = round(clip_euler[i] - idle_euler[i], 1)
                if abs(d) >= 0.5:  # 0.5 Grad Threshold (fast alles mitnehmen)
                    vals[ax] = d
            if vals:
                bones[bone] = vals

        kfs.append({"t": t_kf, "bones": bones})

    kfs.append({"t": 1.0, "bones": {}})  # Fade-Out
    return kfs, int(duration * 1000), all_bones


def main():
    base = Path(r'C:\DEV\EgonsDash\assets\3d\adam')
    vocab_path = Path(r'C:\DEV\hivecore-v2\config\motor_vocabulary.json')

    # Idle als rohe Quaternions laden
    print("Lade idle_natural.glb (Quaternions)...")
    idle_raw, _ = extract_raw(str(base / 'idle_natural.glb'))
    print(f"  {len(idle_raw)} Bones")

    # Clips extrahieren
    clips = {}
    for name in ['waving_right', 'waving_left', 'head_shake']:
        p = base / f'{name}.glb'
        if not p.exists():
            continue
        print(f"\nExtrahiere {name}...")
        clip_raw, dur = extract_raw(str(p))
        n_orig = len(next(iter(clip_raw.values())))
        print(f"  {n_orig} Original-Frames, {dur:.2f}s")

        kfs, dur_ms, bones = build_keyframes_v3(clip_raw, idle_raw, dur)
        clips[name] = {'keyframes': kfs, 'duration_ms': dur_ms, 'bones': bones}
        print(f"  -> {len(kfs)} Motor-Keyframes, {len(bones)} Bones")

    # Vocabulary laden und updaten
    print(f"\nLade {vocab_path}...")
    with open(vocab_path, 'r', encoding='utf-8') as f:
        vocab = json.load(f)

    words = vocab['motor_vocabulary']['words']

    if 'waving_right' in clips:
        c = clips['waving_right']
        words['winken']['keyframes'] = c['keyframes']
        words['winken']['duration_ms'] = c['duration_ms']
        words['winken']['_fix'] = 'v1.7: ALLE Original-Frames + SLERP-Idle + 0.5deg Threshold'
        print(f"\n  winken: {c['duration_ms']}ms, {len(c['keyframes'])} Frames")

    if 'waving_left' in clips:
        c = clips['waving_left']
        words['winken_links']['keyframes'] = c['keyframes']
        words['winken_links']['duration_ms'] = c['duration_ms']
        words['winken_links']['_fix'] = 'v1.7: ALLE Original-Frames + SLERP-Idle + 0.5deg Threshold'
        print(f"  winken_links: {c['duration_ms']}ms, {len(c['keyframes'])} Frames")

    if 'head_shake' in clips:
        c = clips['head_shake']
        words['kopf_schuetteln']['keyframes'] = c['keyframes']
        words['kopf_schuetteln']['duration_ms'] = c['duration_ms']
        words['kopf_schuetteln']['_fix'] = 'v1.7: ALLE Original-Frames + SLERP-Idle + 0.5deg Threshold'
        print(f"  kopf_schuetteln: {c['duration_ms']}ms, {len(c['keyframes'])} Frames")

    vocab['motor_vocabulary']['version'] = '1.7'
    vocab['motor_vocabulary']['_last_glb_extraction'] = '2026-02-27: v3 ALLE Frames + SLERP Idle-Delta'

    with open(vocab_path, 'w', encoding='utf-8') as f:
        json.dump(vocab, f, indent=2, ensure_ascii=False)

    print(f"\n motor_vocabulary.json v1.7 gespeichert!")

    # Validierung
    with open(vocab_path, 'r', encoding='utf-8') as f:
        json.load(f)
    print("  JSON OK")

    # Statistik
    size = vocab_path.stat().st_size
    print(f"  Dateigroesse: {size/1024:.0f} KB")


if __name__ == '__main__':
    main()
