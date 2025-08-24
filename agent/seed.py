import os
import uuid
import random
from datetime import datetime
import psycopg2
from faker import Faker
from dotenv import load_dotenv

load_dotenv()

# db config
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL not configured. Either set env var DATABASE_URL or provide it in .env"
    )

random.seed(42)

def last_words(text, n=2) -> str:
    parts = text.split()
    return " ".join(parts[-n:]) if parts else ""

def build_master_catalog():
    """
    Returns a list[dict] with keys: name, description, price
    200+ items across smartphones, laptops, TVs, monitors, audio, wearables,
    networking, printers, cameras, drones, storage, peripherals, smart home, consoles.
    """
    products = []

    def add(name, desc, price):
        products.append({
            "name": name,
            "description": desc,
            "price": round(float(price), 2),
        })

    # Smartphones 
    phones = [
        ("Apple", "iPhone 15 Pro", '6.1" Super Retina XDR, A17 Pro, 48MP main, iOS 17'),
        ("Apple", "iPhone 15 Pro Max", '6.7" Super Retina XDR, A17 Pro, 48MP main, iOS 17'),
        ("Samsung", "Galaxy S24", '6.2" Dynamic AMOLED 2X 120Hz, Snapdragon 8 Gen 3, Android 14'),
        ("Samsung", "Galaxy S24 Ultra", '6.8" QHD+ AMOLED 120Hz, 200MP camera, Android 14'),
        ("Google", "Pixel 8", '6.2" Actua display 120Hz, Tensor G3, Android 14'),
        ("Google", "Pixel 8 Pro", '6.7" LTPO 120Hz, Tensor G3, Pro camera tools, Android 14'),
        ("OnePlus", "12", '6.82" AMOLED 120Hz, Snapdragon 8 Gen 3, 50MP triple, Android 14'),
        ("Xiaomi", "13T Pro", '6.67" AMOLED 144Hz, Dimensity 9200+, 120W charging, Android'),
    ]
    phone_storages = [128, 256, 512]
    phone_base_prices = {
        "iPhone 15 Pro": 1199, "iPhone 15 Pro Max": 1299,
        "Galaxy S24": 899, "Galaxy S24 Ultra": 1199,
        "Pixel 8": 699, "Pixel 8 Pro": 999,
        "12": 799, "13T Pro": 749
    }
    for brand, model, spec in phones:
        for storage in phone_storages:
            base = phone_base_prices.get(last_words(model, 2), None)
            if base is None:
                base = phone_base_prices.get(model, 799)
            price = base + (50 if storage == 256 else 150 if storage == 512 else 0)
            name = f"{brand} {model} {storage}GB"
            desc = f"{spec}, {storage}GB storage, 5G, dual-SIM, Gorilla Glass, USB‑C."
            add(name, desc, price)

    # Laptops
    laptops = [
        ("Apple", "MacBook Pro 14 (M3)", "14.2\" Liquid Retina XDR, Apple M3, 8‑core CPU, 10‑core GPU, macOS Sonoma"),
        ("Apple", "MacBook Pro 16 (M3 Pro)", "16.2\" Liquid Retina XDR, M3 Pro, 12‑core CPU, macOS Sonoma"),
        ("Dell", "XPS 15 OLED (2024)", "15.6\" 3.5K OLED touch, Intel Core i9-13900H, RTX 4070, Windows 11 Pro"),
        ("Lenovo", "ThinkPad X1 Carbon Gen 11", "14\" 2.8K OLED, Intel Core i7-1370P, Windows 11 Pro"),
        ("ASUS", "ROG Zephyrus G16", "16\" QHD+ 240Hz, i9-13980HX, RTX 4080, Windows 11"),
        ("HP", "Spectre x360 14", "13.5\" 3:2 OLED, Intel Evo, 16GB RAM, Windows 11"),
        ("Acer", "Swift X 16", "16\" 3.2K OLED, Ryzen 9, RTX 4050, Windows 11"),
        ("MSI", "Stealth 14 Studio", "14\" QHD 240Hz, Intel i7, RTX 4070, Windows 11"),
    ]
    laptop_rams = [16, 32]
    laptop_ssds = [512, 1024]
    laptop_base = {
        "MacBook Pro 14 (M3)": 1999, "MacBook Pro 16 (M3 Pro)": 2499,
        "XPS 15 OLED (2024)": 2199, "ThinkPad X1 Carbon Gen 11": 1899,
        "ROG Zephyrus G16": 2799, "Spectre x360 14": 1599,
        "Swift X 16": 1699, "Stealth 14 Studio": 1899
    }
    for brand, model, spec in laptops:
        for ram in laptop_rams:
            for ssd in laptop_ssds:
                price = laptop_base[model] + (100 if ram == 32 else 0) + (150 if ssd == 1024 else 0)
                name = f"{brand} {model} {ram}GB RAM {ssd}GB SSD"
                desc = f"{spec}, {ram}GB RAM, {ssd}GB SSD, Wi‑Fi 6E, Thunderbolt/USB‑C, backlit keyboard."
                add(name, desc, price)

    # ---- Televisions (16+) ----
    tvs = [
        ("Samsung", "Neo QLED 8K QN900C 65\"", "8K AI upscaling, Quantum Matrix Tech Pro, HDR10+, Dolby Atmos, Tizen OS"),
        ("LG", "OLED evo G3 77\"", "4K OLED, α9 AI Processor Gen6, Dolby Vision/Atmos, webOS, 120Hz HDMI 2.1"),
        ("Sony", "Bravia XR A95L 65\" QD‑OLED", "Cognitive Processor XR, XR Triluminos Pro, Dolby Vision/Atmos, Google TV"),
        ("TCL", "Q7 75\"", "4K QLED, 120Hz panel, HDR Pro+, Google TV, Full Array Local Dimming"),
        ("Hisense", "U8K 65\"", "Mini‑LED ULED, 1500+ nits, Dolby Vision IQ, Filmmaker Mode, Google TV"),
        ("Samsung", "The Frame 55\"", "QLED 4K Art Mode, anti‑glare, Slim Fit Wall Mount, Tizen OS"),
        ("LG", "C3 OLED 65\"", "4K OLED, α9 AI Processor, Dolby Vision/Atmos, webOS, Game Optimizer"),
        ("Sony", "X90L 75\"", "4K Full Array LED, Cognitive Processor XR, Google TV, HDMI 2.1 120Hz"),
    ]
    for brand, model, spec in tvs:
        # 2 variants per model
        for variant in ["Standard", "Soundbar Bundle"]:
            delta = 0 if variant == "Standard" else 300
            base = 1499 + random.randint(0, 1200)
            price = base + delta
            name = f"{brand} {model} ({variant})"
            desc = f"{spec}. Smart TV apps, voice control, ALLM/VRR for gaming, slim bezels."
            add(name, desc, price)

    # Monitors
    monitors = [
        ("Dell", "UltraSharp U2723QE 27\"", "4K IPS Black, USB‑C hub 90W, sRGB/Rec.709, height/tilt swivel"),
        ("LG", "34WP65C 34\" Ultrawide", "3440x1440 21:9, 160Hz, curved VA, HDR10, FreeSync"),
        ("ASUS", "ROG Swift PG279QM 27\"", "2560x1440 IPS, 240Hz, G‑SYNC, DisplayHDR 400"),
        ("Samsung", "Odyssey G7 32\"", "2560x1440 VA, 240Hz, 1000R curve, HDR600"),
        ("BenQ", "PD3220U 32\"", "4K IPS, AQCOLOR, Thunderbolt 3, factory calibrated"),
        ("Gigabyte", "M32U 32\"", "4K 144Hz, KVM, HDMI 2.1, FreeSync Premium Pro"),
        ("Acer", "Nitro XV282K 28\"", "4K 144Hz IPS, HDR400, HDMI 2.1, Agile‑Splendor"),
        ("MSI", "Optix MAG274QRF 27\"", "QHD 165Hz Rapid IPS, KVM, HDR Ready"),
        ("ViewSonic", "VX2758‑2KP‑MHD 27\"", "QHD 144Hz IPS, 1ms MPRT, FreeSync"),
        ("Lenovo", "Legion Y27q‑30 27\"", "QHD 180Hz IPS, 0.5ms MPRT, HDR400"),
    ]
    for brand, model, spec in monitors:
        for refresh in [144, 165]:
            price = 299 + random.randint(50, 450) + (50 if refresh == 165 else 0)
            name = f"{brand} {model} {refresh}Hz"
            desc = f"{spec}, {refresh}Hz gaming performance, low blue light, ergonomic stand, USB hub."
            add(name, desc, price)

    # Headphones, Earbuds 
    headphones = [
        ("Sony", "WH‑1000XM5", "ANC, 30‑hour battery, LDAC, multipoint BT 5.3, USB‑C fast charge"),
        ("Bose", "QuietComfort Ultra", "Spatial audio, adjustable EQ, premium comfort, 24‑hour battery"),
        ("Apple", "AirPods Max", "Active Noise Cancellation, Spatial Audio, H1 chip, aluminum build"),
        ("Sennheiser", "Momentum 4", "ANC, 60‑hour battery, aptX Adaptive, plush ear cushions"),
        ("Bowers & Wilkins", "PX7 S2e", "ANC, 40mm drivers, aptX, premium materials"),
    ]
    earbuds = [
        ("Apple", "AirPods Pro (2nd Gen)", "ANC, Adaptive Transparency, Personalized Spatial Audio, MagSafe"),
        ("Samsung", "Galaxy Buds2 Pro", "24‑bit Hi‑Fi, ANC, seamless Galaxy integration, wireless charging"),
        ("Sony", "WF‑1000XM5", "ANC, small/light design, LDAC, speak‑to‑chat"),
        ("Google", "Pixel Buds Pro", "ANC, silent seal, BT multipoint, wireless charging"),
        ("Jabra", "Elite 8 Active", "IP68, secure fit, ANC, long battery life"),
    ]
    for brand, model, spec in headphones + earbuds:
        price = 129 + random.randint(50, 350)
        name = f"{brand} {model}"
        desc = f"{spec}. Includes carry case, USB‑C cable, and app‑based EQ controls."
        add(name, desc, price)

    # Smartwatches & Wearables
    watches = [
        ("Apple", "Watch Ultra 2 49mm", "S9 SiP, dual‑frequency GPS, 36‑hour battery, 100m water resistance"),
        ("Apple", "Watch Series 9 45mm", "S9 SiP, Always‑On Retina, ECG & blood oxygen, fast charge"),
        ("Samsung", "Galaxy Watch6 Classic 47mm", "Rotating bezel, Wear OS 4, heart rate/ECG, 5ATM"),
        ("Garmin", "Fenix 7 Pro Sapphire", "Solar, multi‑band GPS, advanced training metrics, rugged design"),
        ("Fitbit", "Charge 6", "24/7 heart rate, Google services, sleep tracking, 7‑day battery"),
        ("Google", "Pixel Watch 2", "Wear OS, Fitbit integration, ECG, fall detection"),
        ("Amazfit", "GTR 4", "AMOLED, dual‑band GPS, 14‑day battery, 150+ sports modes"),
        ("Huawei", "Watch GT 4 46mm", "AMOLED, long battery life, fitness & health tracking"),
    ]
    for brand, model, spec in watches:
        for connectivity in ["GPS", "LTE"]:
            delta = 0 if connectivity == "GPS" else 100
            base = 249 + random.randint(50, 400)
            name = f"{brand} {model} ({connectivity})"
            desc = f"{spec}, {connectivity} model, stainless steel case, quick‑release bands, fast charging."
            add(name, desc, base + delta)

    # Gaming Consoles
    consoles = [
        ("Sony", "PlayStation 5", "Ultra HD Blu‑ray, AMD Zen 2 CPU, RDNA 2 GPU, DualSense controller"),
        ("Sony", "PlayStation 5 Digital Edition", "All‑digital, 825GB SSD, up to 120fps, Tempest 3D Audio"),
        ("Microsoft", "Xbox Series X", "12 TFLOPS GPU, 1TB SSD, Dolby Vision/Atmos, Quick Resume"),
        ("Microsoft", "Xbox Series S", "All‑digital, 512GB SSD, 1440p up to 120fps, Compact"),
        ("Nintendo", "Switch OLED", "7\" OLED, 64GB storage, TV dock, Joy‑Con controllers"),
        ("Valve", "Steam Deck OLED 1TB", "7.4\" OLED, AMD APU, SteamOS, PCIe Gen 3 SSD"),
    ]
    for brand, model, spec in consoles:
        price = 299 + random.randint(100, 400)
        add(f"{brand} {model}", f"{spec}. Includes HDMI cable and power adapter.", price)

    # Routers
    routers = [
        ("Netgear", "Nighthawk RAXE500", "Wi‑Fi 6E tri‑band, up to 10.8Gbps, 2.5G WAN, WPA3"),
        ("ASUS", "ROG Rapture GT‑AX11000", "Wi‑Fi 6 tri‑band, 2.5G port, gaming QoS, AiMesh"),
        ("TP‑Link", "Archer AX6000", "Wi‑Fi 6 dual‑band, 8x LAN, HomeCare security, OFDMA"),
        ("Linksys", "Hydra Pro 6E", "Wi‑Fi 6E tri‑band, Intelligent Mesh, app control"),
        ("Google", "Nest WiFi Pro", "Wi‑Fi 6E mesh, simple setup, automatic updates"),
        ("Eero", "Pro 6E", "Wi‑Fi 6E mesh, multi‑gig, Zigbee, Matter support"),
        ("Ubiquiti", "UniFi Dream Router", "Wi‑Fi 6 dual‑band, UniFi OS, integrated security gateway"),
        ("Synology", "RT6600ax", "Wi‑Fi 6 tri‑band, SRM 1.3, VLAN/SSIDs, 2.5GbE"),
        ("D‑Link", "Eagle Pro AI M32", "Wi‑Fi 6 mesh, AI steering, WPA3, app‑based setup"),
    ]
    for brand, model, spec in routers:
        price = 149 + random.randint(30, 350)
        add(f"{brand} {model}", f"{spec}. Parental controls, guest network, WPA3 security.", price)
    # Mesh kits 
    mesh_kits = [
        ("TP‑Link", "Deco XE75 (2‑Pack)", "Wi‑Fi 6E tri‑band mesh, up to 5,500 sq ft, AI‑driven mesh"),
        ("Netgear", "Orbi RBKE963 (3‑Pack)", "Quad‑band 6E mesh, 10.8Gbps, dedicated backhaul, 12‑stream"),
        ("ASUS", "ZenWiFi ET8 (2‑Pack)", "Wi‑Fi 6E mesh, AiMesh, 2.5G WAN, app management"),
        ("Eero", "Pro 6 (3‑Pack)", "Wi‑Fi 6 mesh, TrueMesh, Zigbee hub, automatic updates"),
        ("Google", "Nest Wifi (2‑Pack)", "Dual‑band mesh, simple setup, hands‑free help"),
    ]
    for brand, model, spec in mesh_kits:
        price = 249 + random.randint(50, 600)
        add(f"{brand} {model}", f"{spec}. Whole‑home coverage with fast roaming.", price)

    # Printers & Scanners
    printers = [
        ("HP", "LaserJet Pro M404dn", "Monochrome laser, duplex printing, Ethernet, 40 ppm"),
        ("HP", "OfficeJet Pro 9025e", "Color inkjet, AIO, duplex, ADF, Wi‑Fi"),
        ("Canon", "PIXMA G7020 MegaTank", "Supertank inkjet, AIO, low CPP, Wi‑Fi"),
        ("Epson", "EcoTank ET‑4760", "Supertank AIO, ADF, Ethernet/Wi‑Fi, voice‑activated"),
        ("Brother", "HL‑L2395DW", "Mono laser, flatbed scan, duplex, Wi‑Fi Direct"),
        ("Brother", "MFC‑L3770CDW", "Color laser AIO, duplex print/scan, 50‑sheet ADF"),
        ("Canon", "imageCLASS MF455dw", "Mono laser AIO, 40 ppm, duplex, 50‑sheet ADF"),
        ("Epson", "WorkForce Pro WF‑7840", "Wide‑format inkjet AIO, duplex, dual trays"),
        ("HP", "DeskJet 4155e", "Entry AIO inkjet, mobile printing, Wi‑Fi"),
        ("Canon", "CanoScan LiDE 400", "Slim flatbed scanner, 4800x4800 dpi, USB‑powered"),
        ("Epson", "Perfection V600", "Photo/film scanner, 6400 x 9600 dpi, Digital ICE"),
        ("Fujitsu", "ScanSnap iX1600", "Sheet‑fed scanner, 40 ppm, Wi‑Fi, touch screen"),
        ("Brother", "ADS‑1700W", "Compact sheet‑fed scanner, duplex, Wi‑Fi"),
        ("Plustek", "Photo Scanner ePhoto Z300", "Photo feeder scanner, 300 dpi, USB"),
        ("Xerox", "B225", "Mono laser AIO, duplex, 36 ppm, Ethernet/Wi‑Fi"),
    ]
    for brand, model, spec in printers:
        price = 89 + random.randint(60, 500)
        add(f"{brand} {model}", f"{spec}. Includes starter cartridges/ink and setup guide.", price)

    # Cameras
    cameras = [
        ("Canon", "EOS R8", "24.2MP full‑frame, 4K60 oversampled, Dual Pixel AF II"),
        ("Canon", "EOS R6 Mark II", "24.2MP full‑frame, 4K60, IBIS, advanced AF"),
        ("Sony", "Alpha a7 IV", "33MP full‑frame, 4K60 10‑bit, Real‑time Tracking AF"),
        ("Sony", "ZV‑E1", "12MP full‑frame vlogging, 4K120, AI framing, lightweight"),
        ("Nikon", "Z6 II", "24.5MP full‑frame, dual EXPEED 6, 4K60, IBIS"),
        ("Fujifilm", "X‑T5", "40MP APS‑C, 6.2K oversampled 4K, film simulations"),
        ("Panasonic", "Lumix S5 II", "24MP full‑frame, Phase‑Hybrid AF, 4K60 10‑bit"),
        ("GoPro", "HERO12 Black", "5.3K60, HyperSmooth 6.0, 10‑bit color, waterproof 33ft"),
        ("DJI", "Osmo Action 4", "4K120, 1/1.3\" sensor, 10‑bit D‑Log M, magnetic mount"),
        ("Canon", "EOS R50", "24.2MP APS‑C, compact, 4K30 oversampled, beginner‑friendly"),
        ("Sony", "Alpha a6700", "26MP APS‑C, 4K120, AI subject recognition, compact"),
        ("Insta360", "X3", "5.7K 360° action cam, Active HDR, FlowState stabilization"),
    ]
    for brand, model, spec in cameras:
        price = 299 + random.randint(200, 1600)
        add(f"{brand} {model}", f"{spec}. Includes battery, charger, USB‑C cable.", price)

    # Drones
    drones = [
        ("DJI", "Mavic 3 Classic", "4/3 CMOS Hasselblad, 5.1K video, APAS 5.0, 46‑min flight"),
        ("DJI", "Air 3", "Dual‑camera, 4K60 HDR, omnidirectional sensing, 46‑min flight"),
        ("DJI", "Mini 4 Pro", "Under 249g, 4K60 HDR, omnidirectional obstacle sensing"),
        ("Autel", "EVO Lite+", "1\" CMOS, 6K video, RYYB sensor, 40‑min flight"),
        ("Parrot", "Anafi", "4K HDR, 180° tilt gimbal, compact folding design"),
        ("Ryze", "Tello", "Educational mini‑drone, 5MP, 13‑min flight, easy control"),
        ("DJI", "Avata 2", "Cinewhoop FPV, 4K60, RockSteady, Motion Controller"),
        ("Autel", "EVO Nano+", "Ultra‑light, 1/1.28\" sensor, 50MP, obstacle avoidance"),
    ]
    for brand, model, spec in drones:
        price = 99 + random.randint(150, 1800)
        add(f"{brand} {model}", f"{spec}. Includes remote controller and spare props.", price)

    # Storage
    ssds = [
        ("Samsung", "990 PRO 1TB NVMe", "PCIe 4.0 x4, up to 7450MB/s read, heatsink optional"),
        ("Samsung", "990 PRO 2TB NVMe", "PCIe 4.0 x4, up to 7450MB/s read, heatsink optional"),
        ("WD", "Black SN850X 1TB NVMe", "PCIe 4.0, Game Mode 2.0, up to 7300MB/s"),
        ("WD", "Black SN850X 2TB NVMe", "PCIe 4.0, Game Mode 2.0, up to 7300MB/s"),
        ("Crucial", "T700 2TB NVMe", "PCIe 5.0, up to 12400MB/s, heatsink"),
        ("Seagate", "FireCuda 530 1TB NVMe", "PCIe 4.0, up to 7300MB/s, endurance 1275 TBW"),
        ("Kingston", "KC3000 2TB NVMe", "PCIe 4.0, up to 7000MB/s, slim form factor"),
        ("Samsung", "T7 Shield 2TB", "Portable SSD, USB‑C 10Gbps, IP65, rugged"),
        ("SanDisk", "Extreme Portable 1TB", "Portable SSD, USB 10Gbps, IP55, compact"),
        ("Seagate", "Expansion 4TB", "External HDD, USB 3.0, plug‑and‑play"),
        ("WD", "My Passport 5TB", "External HDD, hardware encryption, backup software"),
        ("Synology", "DS224+ NAS", "2‑bay NAS, Intel Celeron, Synology DSM, Btrfs"),
        ("QNAP", "TS‑264", "2‑bay NAS, Intel Celeron, 2.5GbE, PCIe expansion"),
        ("SanDisk", "Ultra Flair 256GB", "USB 3.0 flash drive, metal casing, compact"),
        ("Kingston", "DataTraveler 128GB", "USB 3.2 flash, keyring loop, cap design"),
    ]
    for brand, model, spec in ssds:
        price = 29 + random.randint(30, 400)
        add(f"{brand} {model}", f"{spec}. Suitable for backups, gaming, and creative workflows.", price)

    # Keyboards & Mice 
    keyboards = [
        ("Logitech", "MX Keys S", "Wireless, backlit, Flow cross‑computer, USB‑C"),
        ("Keychron", "K2 Pro", "75% mechanical, hot‑swappable, BT/2.4G, Mac/Win"),
        ("Corsair", "K70 RGB Pro", "Full‑size mechanical, PBT keycaps, media keys"),
        ("Razer", "Huntsman V2", "Optical switches, sound‑dampening foam, USB‑C"),
        ("SteelSeries", "Apex Pro TKL", "OmniPoint adjustable, OLED display, detachable cable"),
        ("Ducky", "One 3 TKL", "Hot‑swap, PBT doubleshot keycaps, solid build"),
        ("Logitech", "G915 TKL", "Low‑profile GL switches, Lightspeed wireless"),
        ("Leopold", "FC660M", "66‑key compact, high‑quality PBT, Cherry switches"),
        ("ASUS", "ROG Azoth", "Wireless 75%, gasket mount, OLED, tri‑mode"),
        ("Akko", "3068B Plus", "65%, tri‑mode, PBT ASA profile, hot‑swap"),
    ]
    mice = [
        ("Logitech", "MX Master 3S", "Ergonomic, 8K sensor, MagSpeed scroll, Flow"),
        ("Razer", "DeathAdder V3 Pro", "Ultra‑light, Focus Pro 30K, 90h battery"),
        ("Logitech", "G Pro X Superlight 2", "Super‑light, HERO 2 sensor, PTFE feet"),
        ("Glorious", "Model O Wireless", "Honeycomb shell, BAMF sensor, 69g"),
        ("SteelSeries", "Aerox 3 Wireless", "Lightweight, AquaBarrier IP54, USB‑C"),
        ("Corsair", "M65 RGB Ultra", "Tunable weight, 26K DPI, sniper button"),
        ("Zowie", "EC2‑C", "Esports shape, driverless, plug‑and‑play"),
        ("ASUS", "ROG Harpe Ace", "Aim Lab tuning, 54g, tri‑mode wireless"),
        ("HyperX", "Pulsefire Haste", "Ultra‑light, TTC golden micro switches"),
        ("Microsoft", "Modern Mobile Mouse", "Slim, Bluetooth, precise wheel, ambidextrous"),
    ]
    for brand, model, spec in keyboards + mice:
        price = 29 + random.randint(30, 220)
        add(f"{brand} {model}", f"{spec}. Includes USB receiver/cable and quick start guide.", price)

    # Smart Home
    smart_home = [
        ("Amazon", "Echo (4th Gen)", "Smart speaker with Alexa, Zigbee hub, multi‑room audio"),
        ("Google", "Nest Hub (2nd Gen)", "7\" display, Sleep Sensing, Google Assistant"),
        ("Google", "Nest Thermostat", "Energy‑saving thermostat, remote control, schedules"),
        ("Ring", "Video Doorbell 4", "1080p HD video, dual‑band Wi‑Fi, quick‑release battery"),
        ("Philips", "Hue White & Color (Starter Kit)", "Bridge + 2 bulbs, 16M colors, app/voice control"),
        ("TP‑Link", "Kasa Smart Plug KP125", "Wi‑Fi plug, energy monitoring, schedules"),
        ("Arlo", "Pro 5S 2K", "2K HDR security camera, color night vision, spotlight"),
        ("Eufy", "RoboVac G30", "Robot vacuum, Smart Dynamic Navigation 2.0, app control"),
        ("Nanoleaf", "Shapes Hexagons (Starter Kit)", "Modular light panels, scenes, music visualization"),
        ("Google", "Nest Protect (2nd Gen)", "Smoke & CO alarm, phone alerts, self‑test"),
    ]
    for brand, model, spec in smart_home:
        price = 24 + random.randint(30, 250)
        add(f"{brand} {model}", f"{spec}. Easy setup with step‑by‑step app guidance.", price)

    # Speakers
    speakers = [
        ("Sonos", "Beam (Gen 2)", "Compact Dolby Atmos soundbar, Wi‑Fi, voice assistants"),
        ("Sonos", "Era 100", "Smart speaker, stereo sound, Trueplay, Wi‑Fi/Bluetooth"),
        ("Bose", "Smart Soundbar 600", "Dolby Atmos, Alexa/Assistant, ADAPTiQ audio"),
        ("JBL", "Bar 500", "5.1-channel soundbar with MultiBeam, Wi‑Fi/BT"),
        ("Sony", "HT‑A3000", "3.1ch soundbar, Dolby Atmos, 360 Spatial Sound Mapping"),
        ("Samsung", "HW‑Q800C", "3.1.2ch, Q‑Symphony, Wireless Dolby Atmos, subwoofer"),
        ("LG", "S75Q", "3.1.2ch soundbar, Meridian tuning, Dolby Atmos"),
        ("Marshall", "Emberton II", "Portable BT speaker, IP67, 30+ hours battery"),
        ("Ultimate Ears", "BOOM 3", "Portable waterproof BT speaker, 360° sound"),
        ("Anker", "Soundcore Motion+", "Hi‑Res BT speaker, USB‑C, 12h battery"),
    ]
    for brand, model, spec in speakers:
        price = 59 + random.randint(50, 550)
        add(f"{brand} {model}", f"{spec}. Includes power cable and wall‑mounting guide (where applicable).", price)

    return products

def expand_products(base_products, multiplier=1):
    """
    Expand products into price/stock variants. The multiplier does not change name/description
    to preserve clean embeddings; it only adjusts price slightly and assigns stock.
    """
    expanded = []
    for product in base_products:
        for _ in range(max(1, int(multiplier))):
            variant = dict(product)
            variant["stock_quantity"] = random.randint(8, 250)
            jitter = random.uniform(0.95, 1.08)
            variant["price"] = round(product["price"] * jitter, 2)
            expanded.append(variant)
    return expanded

def create_tables(conn, drop_existing=True):
    with conn.cursor() as cur:
        if drop_existing:
            cur.execute("DROP TABLE IF EXISTS order_items CASCADE;")
            cur.execute("DROP TABLE IF EXISTS orders CASCADE;")
            cur.execute("DROP TABLE IF EXISTS products CASCADE;")
            cur.execute("DROP TABLE IF EXISTS users CASCADE;")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            address TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price NUMERIC(10,2) NOT NULL,
            stock_quantity INTEGER NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id SERIAL PRIMARY KEY,
            order_number VARCHAR(255) UNIQUE NOT NULL,
            user_id INTEGER REFERENCES users(user_id),
            order_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(50) NOT NULL,
            total_amount NUMERIC(10,2) NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id SERIAL PRIMARY KEY,
            order_id INTEGER REFERENCES orders(order_id),
            product_id INTEGER REFERENCES products(product_id),
            quantity INTEGER NOT NULL,
            price NUMERIC(10,2) NOT NULL
        );
        """)
        conn.commit()

def seed_data(
    conn,
    num_users=5000,
    num_orders=30000,
    product_variant_multiplier=1  # master catalog is already big; set >1 to explode SKUs
):
    fake = Faker()
    with conn.cursor() as cur:
        # Users
        for _ in range(num_users):
            cur.execute(
                "INSERT INTO users (name, address) VALUES (%s, %s)",
                (fake.name(), fake.address().replace("\n", ", ")),
            )

        # Products
        master = build_master_catalog()
        product_list = expand_products(master, multiplier=product_variant_multiplier)
        for p in product_list:
            cur.execute(
                "INSERT INTO products (name, description, price, stock_quantity) VALUES (%s, %s, %s, %s)",
                (p["name"], p["description"], p["price"], p["stock_quantity"]),
            )

        # IDs 
        cur.execute("SELECT user_id FROM users")
        user_ids = [r[0] for r in cur.fetchall()]

        cur.execute("SELECT product_id, price FROM products")
        product_rows = cur.fetchall()
        product_ids = [r[0] for r in product_rows]
        price_map = {pid: float(price) for pid, price in product_rows}

        # orders & items
        statuses = ["pending", "shipped", "delivered", "cancelled"]
        # most are delivered/shipped
        status_weights = [0.15, 0.35, 0.45, 0.05]

        for _ in range(num_orders):
            user_id = random.choice(user_ids)
            order_date = fake.date_time_between(start_date="-3y", end_date="now")
            status = random.choices(statuses, weights=status_weights, k=1)[0]
            order_number = f"ORD-{uuid.uuid4()}"
            cur.execute(
                "INSERT INTO orders (order_number, user_id, order_date, status, total_amount) "
                "VALUES (%s, %s, %s, %s, 0) RETURNING order_id",
                (order_number, user_id, order_date, status),
            )
            order_id = cur.fetchone()[0]

            num_items = random.randint(1, 5)
            total = 0.0
            chosen = random.sample(product_ids, k=num_items)
            for pid in chosen:
                qty = random.randint(1, 3)
                price = price_map[pid]
                total += price * qty
                cur.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
                    (order_id, pid, qty, price),
                )

            cur.execute(
                "UPDATE orders SET total_amount = %s WHERE order_id = %s",
                (round(total, 2), order_id),
            )

        conn.commit()

def main():
    print(f"[{datetime.utcnow().isoformat()}] Connecting to PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    try:
        print("Creating tables...")
        create_tables(conn, drop_existing=True)
        print("Seeding data... (this may take a while for large sizes)")
        seed_data(
            conn,
            num_users=int(os.getenv("SEED_USERS", "5000")),
            num_orders=int(os.getenv("SEED_ORDERS", "30000")),
            product_variant_multiplier=int(os.getenv("SEED_VARIANTS", "1"))
        )
        print("Done.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
