from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer, QEvent
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QScrollArea

from electrum_grs.i18n import _
from electrum_grs.wizard import TermsOfUseWizard
from electrum_grs.gui.qt.util import icon_path, WWLabel
from electrum_grs.gui import messages
from .wizard import QEAbstractWizard, WizardComponent

if TYPE_CHECKING:
    from electrum_grs.simple_config import SimpleConfig
    from electrum_grs.gui.qt import QElectrumApplication


class QETermsOfUseWizard(TermsOfUseWizard, QEAbstractWizard):
    def __init__(self, config: 'SimpleConfig', app: 'QElectrumApplication'):
        TermsOfUseWizard.__init__(self, config)
        QEAbstractWizard.__init__(self, config, app)
        self.window_title = _('Terms of Use')
        self.finish_label = _('I Accept')
        self.title.setVisible(False)
        # self.window().setMinimumHeight(565)  # Enough to show the whole text without scrolling
        self.next_button.setToolTip("You accept the Terms of Use by clicking this button.")

        # attach gui classes
        self.navmap_merge({
            'terms_of_use': {'gui': WCTermsOfUseScreen, 'params': {'icon': ''}},
        })

class WCTermsOfUseScreen(WizardComponent):
    def __init__(self, parent, wizard):
        WizardComponent.__init__(self, parent, wizard, title='')
        self.wizard_title = _('Electrum-GRS Terms of Use')
        self.img_label = QLabel()
        pixmap = QPixmap(icon_path('electrum_darkblue_1.png'))
        self.img_label.setPixmap(pixmap)
        self.img_label2 = QLabel()
        pixmap = QPixmap(icon_path('electrum_text.png'))
        self.img_label2.setPixmap(pixmap)
        hbox_img = QHBoxLayout()
        hbox_img.addStretch(1)
        hbox_img.addWidget(self.img_label)
        hbox_img.addWidget(self.img_label2)
        hbox_img.addStretch(1)

        self.layout().addLayout(hbox_img)
        self.layout().addSpacing(15)

        self.tos_label = WWLabel()
        self.tos_label.setText(messages.MSG_TERMS_OF_USE)
        self.layout().addWidget(self.tos_label)
        self._valid = False

        # Find the scroll area and connect to its scrollbar
        QTimer.singleShot(100, self.check_scroll_position)
        self.window().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.window() and event.type() == QEvent.Type.Resize:
            # catch window resize events to check if the scrollbar is visible
            QTimer.singleShot(100, self.check_scroll_position)
        return super().eventFilter(obj, event)

    def check_scroll_position(self):
        scroll_area = self.window().findChild(QScrollArea)
        if scroll_area and scroll_area.verticalScrollBar() \
                and scroll_area.verticalScrollBar().isVisible():
            scrollbar = scroll_area.verticalScrollBar()
            def on_scroll_change(value):
                if value >= scrollbar.maximum() - 5:  # Allow 5 pixel margin
                    self._valid = True
                    self.on_updated()
            scrollbar.valueChanged.connect(on_scroll_change)
        else:
            # scrollbar is not visible or not found
            self._valid = True
            self.on_updated()

    def apply(self):
        pass
