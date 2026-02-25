"""Setzt die Inner Voice permanent auf PRIVAT.

Nach dem A/B Test haben wir nachgewiesen dass der Observer Effect
Evas Authentizitaet beeintraechtigt. Die Inner Voice bleibt jetzt
permanent privat — sie wird generiert und gespeichert, aber Eva
sieht ihre eigenen Gedanken nicht mehr.
"""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

host = '159.69.157.42'
user = 'root'
pw = 'z##rPK$7pahrwQ2H67kR'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pw)

# Flag-File permanent setzen
stdin, stdout, stderr = ssh.exec_command('touch /opt/hivecore-v2/.inner_voice_hidden')
stdout.read()

# Verifizieren
stdin, stdout, stderr = ssh.exec_command('test -f /opt/hivecore-v2/.inner_voice_hidden && echo "PRIVATE (Flag gesetzt)" || echo "SICHTBAR (kein Flag)"')
print(f'Inner Voice Status: {stdout.read().decode("utf-8").strip()}')

# Service kurz testen
stdin, stdout, stderr = ssh.exec_command('systemctl is-active hivecore')
print(f'Service: {stdout.read().decode("utf-8").strip()}')

ssh.close()
print('Inner Voice ist jetzt PERMANENT PRIVAT.')
print('Eva generiert weiterhin Gedanken, sieht sie aber nicht mehr.')
