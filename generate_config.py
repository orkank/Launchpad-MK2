import json

def get_host_address():
    """Get host address from user"""
    while True:
        host = input("\nEnter host IP address (or press Enter for localhost): ").strip()
        if host == "":
            return "localhost"

        # Simple IP validation
        try:
            parts = host.split('.')
            if len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts):
                return host
            print("Invalid IP address format. Please use format: xxx.xxx.xxx.xxx")
        except:
            print("Invalid IP address format. Please use format: xxx.xxx.xxx.xxx")

def generate_homebridge_config(animations, port=3000):
    """Generate Homebridge config for all animations"""
    host = get_host_address()
    base_url = f"http://{host}:{port}"
    print(f"\nUsing base URL: {base_url}")

    accessories = [
        # Spotify Power
        {
            "accessory": "HTTP-SWITCH",
            "name": "Spotify Controller",
            "switchType": "stateful",
            "onUrl": f"{base_url}/power",
            "offUrl": f"{base_url}/power",
            "statusUrl": f"{base_url}/status",
            "pullInterval": 5000
        },
        # Spotify Play/Pause
        {
            "accessory": "HTTP-SWITCH",
            "name": "Spotify Play/Pause",
            "switchType": "stateful",
            "onUrl": f"{base_url}/play",
            "offUrl": f"{base_url}/play",
            "statusUrl": f"{base_url}/status",
            "pullInterval": 5000
        },
        # Volume Control
        {
            "accessory": "HTTP-LIGHTBULB",
            "name": "Spotify Volume",
            "onUrl": f"{base_url}/volume",
            "offUrl": f"{base_url}/volume",
            "statusUrl": f"{base_url}/status",
            "brightness": {
                "url": f"{base_url}/volume",
                "statusUrl": f"{base_url}/volume"
            }
        }
    ]

    # Add animation switches
    for anim_name in animations:
        switch = {
            "accessory": "HTTP-SWITCH",
            "name": f"{anim_name.title()} Animation",
            "switchType": "stateful",
            "onUrl": {
                "url": f"{base_url}/animation",
                "method": "PUT",
                "body": {"name": anim_name}
            },
            "offUrl": {
                "url": f"{base_url}/animation",
                "method": "PUT",
                "body": {"name": "none"}
            },
            "statusUrl": f"{base_url}/animation",
            "statusPattern": anim_name,
            "pullInterval": 5000
        }
        accessories.append(switch)

    return {"accessories": accessories}

if __name__ == "__main__":
    print("Homebridge Config Generator for Launchpad MK2 Spotify Controller")
    print("=" * 60)

    # Example animations list
    animations = ["rainbow", "matrix", "equalizer", "classical", "electronic"]
    config = generate_homebridge_config(animations)

    filename = "homebridge_config.json"
    with open(filename, "w") as f:
        json.dump(config, f, indent=4)

    print(f"\nConfiguration saved to {filename}")
    print("Add this configuration to your Homebridge config.json")