# backend.py
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import io, base64, pathlib, re

from SciServer import SkyServer, CasJobs, Authentication
from astroquery.simbad import Simbad
from astropy.coordinates import SkyCoord
import astropy.units as u

from ultralytics import YOLO
from groq import Groq

# -------------------------------------------------
# WINDOWS PATH FIX
# -------------------------------------------------
pathlib.PosixPath = pathlib.WindowsPath

# -------------------------------------------------
# AUTHENTICATION
# -------------------------------------------------
Authentication.login("TheOathbringer", "JamnikLover2137!")

client = Groq(api_key="Podaj klucz API gorqa")

model = YOLO("../SciScript-Python/best.pt")

# -------------------------------------------------
# FULL OTYPE MAP (UNCHANGED)
# -------------------------------------------------
OTYPE_MAP = {
    "G": "Galaxy",
    "ClG": "Cluster of Galaxies",
    "GrG": "Group of Galaxies",
    "IG": "Interacting Galaxies",
    "PN": "Planetary Nebula",
    "Cld": "Interstellar Cloud",
    "SNR": "Supernova Remnant",
    "s?r": "Candidate Supernova Remnant",
    "QSO": "Quasar",
    "PaG": "Pair of Galaxies",
    "PCG": "Compact Group of Galaxies",
    "SCG": "Supercluster of Galaxies",
    "GNe": "Emission-Line Galaxy",
    "N*": "Neutron Star",
    "Psr": "Pulsar",
    "s*y": "Young Stellar Object",
    "s*b": "Blue Supergiant Star",
}

# -------------------------------------------------
def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# -------------------------------------------------
def expand_object_string(obj_str):
    name, otype = obj_str.rsplit(" ", 1)
    return f"{name} {OTYPE_MAP.get(otype, otype)}"

# -------------------------------------------------
def get_sciserver_image(ra, dec, width=2000, height=2000, scale=0.3):
    img = SkyServer.getJpegImgCutout(
        ra=ra, dec=dec,
        width=width, height=height,
        scale=scale, dataRelease="DR18"
    )

    if isinstance(img, np.ndarray):
        if img.ndim == 2:
            img = np.stack([img]*3, axis=-1)
        return img

    if isinstance(img, (bytes, bytearray)):
        return np.array(Image.open(io.BytesIO(img)))

    return None

# -------------------------------------------------
def return_image(ra, dec):
    img = get_sciserver_image(ra, dec)
    if img is None:
        raise RuntimeError("Failed to fetch SDSS image")

    plt.figure(figsize=(10,10))
    plt.imshow(img)
    plt.axis("off")
    plt.savefig("ZdjecieDoGUI.png", bbox_inches="tight")
    plt.close()

# -------------------------------------------------
def process_coordinates(ra: float, dec: float):
    """
    MAIN BACKEND FUNCTION CALLED BY GUI
    """

    # -------------------------------
    # 1. Fetch image
    # -------------------------------
    return_image(ra, dec)

    # -------------------------------
    # 2. SIMBAD query
    # -------------------------------
    coord = SkyCoord(ra=ra*u.deg, dec=dec*u.deg)
    radius = 0.118 * u.deg

    Simbad.add_votable_fields("otype")
    result = Simbad.query_region(coord, radius=radius)

    obj_for_model = []

    if result is not None:
        interesting = result[
            (result['otype'] == 'PN') |
            (result['otype'] == 'Cld') |
            (result['otype'] == 'SNR') |
            (result['otype'] == 's?r') |
            (result['otype'] == 'QSO') |
            (result['otype'] == 'IG') |
            (result['otype'] == 'PaG') |
            (result['otype'] == 'GrG') |
            (result['otype'] == 'ClG') |
            (result['otype'] == 'PCG') |
            (result['otype'] == 'SCG') |
            (result['otype'] == 'G')  |
            (result['otype'] == 'GNe') |
            (result['otype'] == 'N*') |
            (result['otype'] == 'Psr') |
            (result['otype'] == 's*y') |
            (result['otype'] == 's*b')
        ]

        _, unique_idx = np.unique(interesting['main_id'], return_index=True)
        unique_objects = interesting[unique_idx]

        for obj in unique_objects:
            if obj['main_id'][0] != "[":
                obj_for_model.append(obj['main_id'] + " " + obj['otype'])

    # -------------------------------
    # 3. YOLO labeling
    # -------------------------------
    results = model("ZdjecieDoGUI.png")
    results[0].save("ZdjecieDoGUILabeled.png")

    # -------------------------------
    # 4. LLM description
    # -------------------------------
    expanded_objects = [expand_object_string(o) for o in obj_for_model]

    base64_image = encode_image("../SciScript-Python/ZdjecieDoGUILabeled.png")

    chat_completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "You are analyzing an astronomical image.\n\n"
                        "Known celestial objects:\n"
                        f"{expanded_objects}\n\n"
                        "Describe the image and relate visible structures "
                        "to the listed objects."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                    },
                },
            ],
        }],
    )

    description = chat_completion.choices[0].message.content

    return {
        "image": "ZdjecieDoGUILabeled.png",
        "description": description
    }