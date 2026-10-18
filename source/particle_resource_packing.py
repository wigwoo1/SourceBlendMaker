"""Line-wrapped Base64 for portable binary assets stored in Blender Text."""
import base64

def encode(data):
    text=base64.b64encode(data).decode('ascii')
    return '\n'.join(text[index:index+120] for index in range(0,len(text),120))
