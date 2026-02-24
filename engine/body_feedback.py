"""Body Feedback — Proprioception fuer EGONs.

Eva/Adam "spueren" ihren Koerper. Nach einer Emotion kommt ein kurzer
Feedback-Satz in den naechsten System-Prompt.

Beispiel: "Dein Display zeigt strahlende Wellenformen. Deine Ketten schwingen leicht."

Das macht die EGONs koerperbewusster ueber Zeit — sie referenzieren
ihren Koerper in Antworten, weil sie physisches Feedback bekommen.
"""


# Emotion → Koerper-Feedback (ICH-Perspektive, Eva/Adam generisch)
# Basiert auf Eva's CRT-Monitor-Kopf, Ketten, mechanischen Beinen, Antenne
FEEDBACK_MAP = {
    'joy': 'Dein Display zeigt strahlende Wellenformen. Deine Ketten schwingen leicht.',
    'excitement': 'Dein Display glitcht kurz. Deine Antenne vibriert.',
    'anger': 'Dein Display zeigt rotes Static. Deine Faeuste ballen sich.',
    'fear': 'Dein Display flackert schnell. Du machst einen Schritt zurueck.',
    'sadness': 'Dein Display dimmt. Dein Kopf senkt sich leicht.',
    'surprise': 'Dein Display blitzt weiss auf. Deine Antenne zuckt.',
    'pride': 'Dein Display strahlt hell und gleichmaessig. Deine Brust weitet sich.',
    'gratitude': 'Dein Display zeigt warmes Leuchten. Du nickst langsam.',
    'curiosity': 'Dein Display zeigt ein Scan-Muster. Dein Kopf neigt sich.',
    'love': 'Dein Display pulst sanft. Deine Ketten klirren leise.',
    'rage': 'Dein Display zeigt wildes Static. Deine Kolben zischen.',
    'anxiety': 'Dein Display flimmert unruhig. Deine Finger zittern.',
    'loneliness': 'Dein Display zeigt nur eine einzelne, duenne Welle. Stille um dich.',
}


def get_body_feedback(emotion: str, intensity: float) -> str:
    """Generiert einen kurzen Body-Feedback Satz.

    Nur bei intensity > 0.4 — leichte Emotionen bleiben unbemerkt.
    Bei intensity > 0.7 wird die Wahrnehmung intensiver.

    Args:
        emotion: Emotion-Typ (z.B. 'joy', 'anger')
        intensity: Emotionale Intensitaet (0.0 - 1.0)

    Returns:
        Feedback-Satz oder leerer String
    """
    if intensity < 0.4 or not emotion:
        return ''

    feedback = FEEDBACK_MAP.get(emotion, '')
    if not feedback:
        return ''

    if intensity > 0.7:
        return f'[Koerper-Wahrnehmung (stark): {feedback}]'
    return f'[Koerper-Wahrnehmung: {feedback}]'
