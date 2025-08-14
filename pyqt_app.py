#!/usr/bin/env python3
"""
Mininet-PoP - PyQt6 Frontend
"""
import sys
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsTextItem, QGraphicsLineItem, QGraphicsItem, QDialog,
    QFormLayout, QLineEdit, QDialogButtonBox, QMessageBox, QHBoxLayout
)
from PyQt6.QtGui import QColor, QPen, QBrush
from PyQt6.QtCore import Qt, QPointF, QTimer

# Add the project root to the Python path
sys.path.insert(0, '.')
from backend_api import BackendAPI

class EditDialog(QDialog):
    def __init__(self, title, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        self.layout = QFormLayout(self)
        self.inputs = {}

        for key, value in data.items():
            self.inputs[key] = QLineEdit(str(value))
            self.layout.addRow(key, self.inputs[key])

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def get_data(self):
        return {key: widget.text() for key, widget in self.inputs.items()}

class LinkItem(QGraphicsLineItem):
    # ... (code from previous step, unchanged)
    def __init__(self, source_node, target_node):
        super().__init__()
        self.source = source_node
        self.target = target_node
        self.setZValue(-1)
        self.setPen(QPen(QColor("black"), 2))

    def update_position(self):
        self.setLine(
            self.source.pos().x(), self.source.pos().y(),
            self.target.pos().x(), self.target.pos().y()
        )

class NodeItem(QGraphicsItem):
    def __init__(self, node_data, main_window):
        super().__init__()
        self.node_data = node_data
        self.main_window = main_window
        self.links = []

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

        self.setPos(QPointF(node_data['x'], node_data['y']))

    def add_link(self, link):
        self.links.append(link)

    def boundingRect(self):
        return QRectF(-25, -25, 50, 50)

    def paint(self, painter, option, widget):
        pass # Implemented in subclasses

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for link in self.links:
                link.update_position()
            self.node_data['x'] = self.pos().x()
            self.node_data['y'] = self.pos().y()
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        if self.main_window.is_experiment_running():
            # In run mode, show stats for hosts
            if self.node_data['type'] == 'host':
                self.show_stats_dialog()
        else:
            # In design mode, show edit dialog
            self.show_edit_dialog()

    def show_edit_dialog(self):
        # Properties to edit in design mode
        editable_props = {}
        if self.node_data['type'] == 'host':
            editable_props['ip'] = self.node_data.get('ip', '10.0.0.1/24')
            editable_props['mac'] = self.node_data.get('mac', '')
        elif self.node_data['type'] == 'switch':
            editable_props['dpid'] = self.node_data.get('dpid', '')

        if not editable_props:
            return

        dialog = EditDialog(f"Edit {self.node_data['id']}", editable_props, self.main_window)
        if dialog.exec():
            new_data = dialog.get_data()
            self.node_data.update(new_data)
            print(f"Updated {self.node_data['id']}: {new_data}")

    def show_stats_dialog(self):
        # Placeholder for showing stats
        stats_dialog = QDialog(self.main_window)
        stats_dialog.setWindowTitle(f"Statistics for {self.node_data['id']}")
        layout = QVBoxLayout()
        stats_label = QLineEdit("Fetching stats...")
        stats_label.setReadOnly(True)
        layout.addWidget(stats_label)
        stats_dialog.setLayout(layout)

        def update_stats():
            result = self.main_window.backend.get_host_stats(self.node_data['id'])
            if result['success']:
                stats_text = json.dumps(result['stats'], indent=2)
                stats_label.setText(stats_text)
            else:
                stats_label.setText(result['error'])

        # Update stats immediately and then every 5 seconds
        update_stats()
        timer = QTimer(stats_dialog)
        timer.timeout.connect(update_stats)
        timer.start(5000)

        stats_dialog.exec()

class HostItem(NodeItem):
    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(QColor("lightblue")))
        painter.setPen(QPen(QColor("black"), 2))
        painter.drawEllipse(-20, -20, 40, 40)

class SwitchItem(NodeItem):
    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(QColor("lightgreen")))
        painter.setPen(QPen(QColor("black"), 2))
        painter.drawRect(-25, -20, 50, 40)

class MainWindow(QMainWindow):
    def __init__(self, backend: BackendAPI):
        super().__init__()
        self.backend = backend
        self.setWindowTitle("Mininet PoP - PyQt Edition")
        self.setGeometry(100, 100, 1200, 800)

        self.node_items = {}
        self.current_topology_data = None
        self._is_running = False

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.start_button = QPushButton("Start Experiment (load 2s4h.json)")
        self.stop_button = QPushButton("Stop Experiment")
        self.attach_cli_button = QPushButton("Attach to CLI")

        self.stop_button.setEnabled(False)
        self.attach_cli_button.setEnabled(False)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.attach_cli_button)
        main_layout.addLayout(controls_layout)

        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 1000, 700)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QApplication.renderHints().Antialiasing)
        main_layout.addWidget(self.view)

        self.start_button.clicked.connect(self.start_experiment)
        self.stop_button.clicked.connect(self.stop_experiment)
        self.attach_cli_button.clicked.connect(self.attach_to_cli)

    def attach_to_cli(self):
        result = self.backend.attach_to_cli()
        if result['success']:
            QMessageBox.information(
                self,
                "Attach to CLI",
                f"To attach to the Mininet CLI, run the following command in a new terminal:\n\n{result['command']}"
            )
        else:
            QMessageBox.warning(
                self,
                "Attach to CLI Error",
                f"Could not attach to CLI: {result['error']}"
            )

    def is_experiment_running(self):
        return self._is_running

    def draw_topology(self):
        self.scene.clear()
        self.node_items = {}
        if not self.current_topology_data: return

        for node_data in self.current_topology_data.get('nodes', []):
            node_id = node_data['id']
            item = HostItem(node_data, self) if node_data['type'] == 'host' else SwitchItem(node_data, self)
            self.scene.addItem(item)
            self.node_items[node_id] = item
            text = QGraphicsTextItem(node_id, item)
            text.setPos(-text.boundingRect().width() / 2, -text.boundingRect().height() / 2)

        for link_data in self.current_topology_data.get('links', []):
            source_id, target_id = link_data['source'], link_data['target']
            if source_id in self.node_items and target_id in self.node_items:
                source_item, target_item = self.node_items[source_id], self.node_items[target_id]
                link_item = LinkItem(source_item, target_item)
                source_item.add_link(link_item)
                target_item.add_link(link_item)
                self.scene.addItem(link_item)
                link_item.update_position()

    def start_experiment(self):
        try:
            with open('2s4h.json', 'r') as f:
                self.current_topology_data = json.load(f)
        except FileNotFoundError:
            print("Error: 2s4h.json not found.")
            return

        self.draw_topology()

        result = self.backend.start_experiment(self.current_topology_data)
        if result['success']:
            print("Experiment started successfully")
            self._is_running = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.attach_cli_button.setEnabled(True)
            for item in self.node_items.values():
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        else:
            print(f"Error starting experiment: {result['error']}")

    def stop_experiment(self):
        result = self.backend.stop_experiment()
        if result['success']:
            print("Experiment stopped successfully")
            self._is_running = False
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.attach_cli_button.setEnabled(False)
            for item in self.node_items.values():
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        else:
            print(f"Error stopping experiment: {result['error']}")

def main():
    app = QApplication(sys.argv)
    backend_api = BackendAPI()
    window = MainWindow(backend_api)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
