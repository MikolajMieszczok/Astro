import sys
from PyQt6.QtCore import QUrl, QPropertyAnimation, Qt
from PyQt6.QtGui import QPixmap, QVector3D
from PyQt6.Qt3DCore import QEntity, QTransform
from PyQt6.Qt3DExtras import QSphereMesh, QDiffuseMapMaterial, Qt3DWindow
from PyQt6.Qt3DRender import QTextureLoader, QPointLight
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QMainWindow,
    QVBoxLayout, QLineEdit, QLabel, QGridLayout,
    QComboBox, QScrollArea
)

from nonsciserverfiles.backend import process_coordinates


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setMouseTracking(True)
        self.layout = QGridLayout()

        # ---------- 3D VIEW ----------
        self.view3d = Qt3DWindow()
        self.container3d = QWidget.createWindowContainer(self.view3d)
        self.scene = QEntity()
        self.earth_sphere = QEntity(self.scene)
        self.camera = self.view3d.camera()
        self.light_entity = QEntity(self.scene)

        # ---------- UI ELEMENTS ----------
        self.space_photo = QLabel()
        self.space_photo.setScaledContents(True)

        self.llm_output = QLabel()
        self.llm_output.setWordWrap(True)
        self.llm_output.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.llm_scroll = QScrollArea()
        self.llm_scroll.setWidgetResizable(True)
        self.llm_scroll.setWidget(self.llm_output)

        self.interestingPlaces = QComboBox()
        self.dec = QLineEdit()
        self.ra = QLineEdit()
        self.generate_button = QPushButton("Retrieve photo of space and description")

        # ---------- WINDOW ----------
        self.setWindowTitle("Space Describer")
        self.resize(1000, 800)

        self.prepare_layout()
        self.prepare_textboxes()
        self.prepare_labels()
        self.prepare_buttons()
        self.prepare_combo_box()
        self.prepare_sphere()
        self.prepare_camera()

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

    # ---------- LAYOUT ----------
    def prepare_layout(self):
        coords_layout = QVBoxLayout()
        coords_layout.addWidget(self.interestingPlaces)
        coords_layout.addWidget(self.ra)
        coords_layout.addWidget(self.dec)
        coords_layout.addWidget(self.generate_button)
        coords_layout.addStretch()

        self.layout.addWidget(self.container3d, 0, 0)
        self.layout.addLayout(coords_layout, 1, 0)

        self.layout.addWidget(self.space_photo, 0, 1)
        self.layout.addWidget(self.llm_scroll, 1, 1)

        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 2)
        self.layout.setRowStretch(0, 3)
        self.layout.setRowStretch(1, 1)

    # ---------- UI PREP ----------
    def prepare_buttons(self):
        self.generate_button.setFixedHeight(50)
        self.generate_button.clicked.connect(self.on_generate_click)

    def prepare_textboxes(self):
        self.ra.setPlaceholderText("Right Ascension (0–360)")
        self.dec.setPlaceholderText("Declination (-11 to 42)")

    def prepare_labels(self):
        self.space_photo.setPixmap(QPixmap("../photos/space.jpg"))
        self.llm_output.setText("Here shall go the description of desired space")

    # ---------- 3D SPHERE ----------
    def prepare_sphere(self):
        sphere_mesh = QSphereMesh()
        sphere_mesh.setRadius(1.0)

        texture = QTextureLoader(self.scene)
        texture.setSource(QUrl.fromLocalFile("./../photos/8k_earth_daymap.png"))

        material = QDiffuseMapMaterial(self.scene)
        material.setDiffuse(texture)

        self.earth_sphere.addComponent(sphere_mesh)
        self.earth_sphere.addComponent(material)

        transform = QTransform()
        self.anim = QPropertyAnimation(transform, b"rotationY")
        self.anim.setStartValue(0)
        self.anim.setEndValue(360)
        self.anim.setDuration(3000)
        self.anim.setLoopCount(-1)
        self.anim.start()

        self.earth_sphere.addComponent(transform)
        self.view3d.setRootEntity(self.scene)

    def prepare_camera(self):
        self.camera.lens().setPerspectiveProjection(45.0, 16 / 9, 0.1, 1000.0)
        self.camera.setPosition(QVector3D(0, 0, 5))
        self.camera.setViewCenter(QVector3D(0, 0, 0))

        light = QPointLight(self.light_entity)
        light.setIntensity(1)
        self.light_entity.addComponent(light)

        light_transform = QTransform()
        light_transform.setTranslation(QVector3D(0, 5, 10))
        self.light_entity.addComponent(light_transform)

    # ---------- COMBO ----------
    def prepare_combo_box(self):
        places = {
            "Stephans Quintet": (338.9896, 33.96),
            "M33 Galaxy": (23.4621, 30.6602),
            "M51 Galaxy": (202.469583, 47.195278),
            "M110 Galaxy": (10.0916, 41.6853),
            "Great Hercules Cluster": (250.423, 36.461),
            "Sombrero Galaxy": (187.706, 12.391),
            "Pleiades": (56.750, 24.117),
        }

        for place, coords in places.items():
            self.interestingPlaces.addItem(place, coords)

        self.interestingPlaces.currentIndexChanged.connect(self.on_place_selected)

    # ---------- ACTIONS ----------
    def on_generate_click(self):
        send_coords_to_backend(
            self.dec.text(),
            self.ra.text(),
            self.llm_output,
            self.space_photo
        )

    def on_place_selected(self, index):
        coords = self.interestingPlaces.itemData(index)
        if coords:
            ra, dec = coords
            self.ra.setText(str(ra))
            self.dec.setText(str(dec))


# ---------- BACKEND ----------
def send_coords_to_backend(dec, ra, llm_output, space_photo):
    try:
        dec = float(dec)
        ra = float(ra)
    except ValueError:
        llm_output.setText("Invalid coordinates.")
        return

    try:
        result = process_coordinates(ra, dec)
        llm_output.setText(result["description"])
        space_photo.setPixmap(QPixmap(result["image"]))
    except Exception as e:
        llm_output.setText(str(e))


# ---------- APP ----------
def prepare_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()