#!/usr/bin/env python3
"""测试 iMessage 发送功能"""
import subprocess

recipient = "+8613901280530"
message = "测试"

escaped_message = message.replace('"', '\\"').replace('\n', '\\n')

script = f'''
tell application "Messages"
    send "{escaped_message}" to buddy "{recipient}"
end tell
'''

result = subprocess.run(
    ["osascript", "-e", script],
    capture_output=True,
    text=True,
    timeout=30
)

print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout}")
print(f"Stderr: {result.stderr}")
