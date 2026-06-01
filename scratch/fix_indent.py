with open("/home/john/Thunderbird/OpsCenter/nexus.py", "r") as f:
    lines = f.readlines()

# Indent should be 12 spaces for line 84
lines[83] = "            if from_opencode:\n"
lines[84] = "                result = dispatch_to_claude(txt, mid_to_use)\n"
lines[85] = "                engine = 'claude'\n"
lines[86] = "            else:\n"
lines[87] = "                engine, result = route_and_dispatch(txt, mid_to_use)\n"

with open("/home/john/Thunderbird/OpsCenter/nexus.py", "w") as f:
    f.writelines(lines)
