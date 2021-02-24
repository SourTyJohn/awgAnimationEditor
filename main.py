import PyQt5.QtWidgets as QW
import PyQt5.uic as uic
import PyQt5.QtCore as QCore
import PyQt5.QtGui as QGui
from PyQt5.QtCore import Qt

from PIL import Image, ImageDraw
from PIL.ImageQt import ImageQt

from os.path import dirname
from easygui import fileopenbox, filesavebox
import numpy as np
from ast import literal_eval

from constants import *
from zpack import from_file, to_file

# { tag: name, }
tags = {}


class ListItem(QW.QListWidgetItem):
    tag: int  # constant


class MainWindow(QW.QMainWindow):
    top_set: QW.QMenu
    top_animation: QW.QMenu

    main_list: QW.QListWidget

    def __init__(self):
        # LOADING RAW UI LAYOUT
        super().__init__()
        uic.loadUi(TEMPLATES_DIR.format('main'), self)
        self.setWindowIcon(QGui.QIcon(LOGO_PATH))

        # PATH DEFAULTS
        self.directory = dirname(__file__)
        self.path_def_animation = self.directory + '/*.png'
        self.path_def_set = self.directory + '/*.animset'

        # PATH
        self.current_set_path = None

        # ANIMATIONS
        self.animations = {}

        # SETTING UP UI
        self.setup()

    def setup(self):
        self.setWindowTitle('animationEditor')

        self.top_set.addAction('open', self.open_set)
        self.top_set.addAction('new', self.new_set)
        self.top_set.addAction('save', self.save_set)
        self.top_animation.addAction('add', self.add_animation_from_png)
        self.main_list.setIconSize(QCore.QSize(128, 128))

        self.main_list.itemClicked.connect(self.edit_animation)

    # TOP MENU BUTTONS
    @QCore.pyqtSlot()
    def add_animation_from_png(self):
        files_paths = fileopenbox(default=self.path_def_animation, multiple=True)
        if not files_paths:
            return

        for file in files_paths:
            name = str(len(self.animations))
            # ANIMATION DATA UPDATE
            frames = frames_count(file)
            delays = [1, ] * frames

            self.animations[name] = {
                'image': Image.open(file), 'delays': delays, 'isAttack': False, 'attackFrames': []
            }

            self.update_list(name, self.animations[name]['image'])

    def update_list(self, name, image):
        # LIST OF ANIMATIONS: VISUAL UPDATE
        item = QW.QListWidgetItem()
        item.setBackground(QGui.QColor(96, 96, 96))
        item.setIcon(QGui.QIcon(QGui.QPixmap.fromImage(ImageQt(image))))
        item.setSizeHint(QCore.QSize(0, 120))
        item.tag = len(self.animations) - 1
        tags[item.tag] = name

        # ADDING ITEM
        self.main_list.addItem(item)
        self.updateAnimationText(item.tag, name)

    def updateAnimationText(self, aindex, name):
        a = self.animations[name]
        text = f'In-set Name> {name}\nDelays> {a["delays"]}\nAttack> {a["isAttack"]}\t{a["attackFrames"]}'
        widget = QW.QLabel(text)
        widget.setFont(QGui.QFont('MS Serif', 16))

        item = self.main_list.item(aindex)
        self.main_list.setItemWidget(item, widget)

    @QCore.pyqtSlot()
    def new_set(self):
        animationWindow.close_()
        self.animations = {}
        self.main_list.clear()
        self.current_set_path = None

    @QCore.pyqtSlot()
    def open_set(self):
        file_path = fileopenbox(default=self.path_def_set)
        if not file_path:
            return

        self.new_set()
        animations = from_file(file_path)

        for anim in animations:
            key = anim[1]['key']
            image = anim[0]
            del anim[1]['key']
            anim[1]['image'] = image
            self.animations[key] = anim[1]
            self.update_list(key, image)

    @QCore.pyqtSlot()
    def save_set(self):
        file_path = filesavebox(default=self.path_def_set)
        if not file_path:
            return

        to_file(file_path, self.animations)

    #
    @QCore.pyqtSlot()
    def edit_animation(self):
        global animationWindow
        index = self.main_list.selectedIndexes()
        if not index:
            return

        index = index[0].row()
        animationWindow = AnimationWindow(index)
        self.hide()
        animationWindow.show()

    def keyPressEvent(self, event: QGui.QKeyEvent):
        if event.key() == Qt.Key_Delete:
            item = self.main_list.takeItem(self.main_list.selectedIndexes()[0].row())
            tag = item.tag
            name = tags[tag]
            del self.animations[name]
            del tags[tag]


class AnimationWindow(QW.QWidget):
    play_button: QW.QPushButton
    play_slider: QW.QSlider

    name_input: QW.QLineEdit
    attack_input: QW.QLineEdit
    delays_input: QW.QLineEdit

    add_delay_button: QW.QPushButton
    sub_delay_button: QW.QPushButton

    add_att_button: QW.QPushButton

    close_save_button: QW.QPushButton
    close_button: QW.QPushButton

    image_label: QW.QLabel

    isattack_box: QW.QCheckBox
    show_attack_box: QW.QCheckBox

    curr_frame_l: QW.QLabel
    curr_time_l: QW.QLabel

    image: Image.Image

    # LOADING RAW UI LAYOUT
    def __init__(self, anim_tag):
        global animationWindowInited
        animationWindowInited = True

        super().__init__()
        # TIMED EVENTS
        self.update_animation = QCore.QTimer()
        self.update_animation.setInterval(INTERVAL)
        self.update_animation.timerEvent = self.animation_step

        # MAIN UI
        uic.loadUi(TEMPLATES_DIR.format('animation'), self)
        self.setWindowIcon(QGui.QIcon(LOGO_PATH))

        # TAG AND ANIMATION LOAD
        self.tag = anim_tag
        name = tags[self.tag]
        self.setWindowTitle(name)
        self.load(name)

        # SUPPLY FLAGS
        self.changed = False
        self.hard_close = False

        # SETTING UP BUTTONS AND SLIDERS
        self.add_delay_button.clicked.connect(self.add_to_all_delays)
        self.sub_delay_button.clicked.connect(self.sub_from_all_delays)
        self.add_att_button.clicked.connect(self.add_attack_frame)

        self.close_button.clicked.connect(self.close_)
        self.close_save_button.clicked.connect(self.close_save)
        self.play_button.clicked.connect(self.play_animation)

        self.name_input.textChanged.connect(self.name_changed)
        self.attack_input.textChanged.connect(self.attack_frames_changed)
        self.delays_input.textChanged.connect(self.delays_changed)
        self.play_slider.valueChanged.connect(self.frame_show)

        # SHOW THE FRAME
        self.delays_changed()

    def play_animation(self):
        if self.update_animation.isActive():
            self.update_animation.stop()
            self.play_button.setText('>play')
        else:
            self.update_animation.start()
            self.play_button.setText('llstop')

    def animation_step(self, a0):
        sld = self.play_slider
        if sld.value() == sld.maximum():
            sld.setValue(0)
        else:
            sld.setValue(sld.value() + 1)

    @property
    def animation(self):
        return window.animations[tags[self.tag]]

    def load(self, name):
        anim = window.animations[name]
        # IMAGE
        self.image = anim['image']

        # LOADING ANIMATION DATA
        self.name_input.setText(name)
        self.attack_input.setText(str(anim['attackFrames']))
        self.delays_input.setText(str(anim['delays']))
        if anim['isAttack']:
            self.isattack_box.click()

    def frame_show(self, time=0):
        # CURRENT FRAME AND TEXT
        current_frame = self.what_frame(time)
        self.curr_frame_l.setText(str(current_frame))
        self.curr_time_l.setText(str(time))

        # COLLECTING DATA
        animation = self.animation
        delays = animation['delays']

        # GETTING CURRENT FRAME'S IMAGE
        c, w = current_frame, self.image.width / len(delays)
        frame = self.image.crop([c * w, 0, (c + 1) * w, self.image.height])

        # SCALING TO FIT LABEL
        scale_ratio = min(self.image_label.width() / frame.width, self.image_label.height() / frame.height)
        frame = scale(frame, scale_ratio)

        # ATTACK
        if self.isattack_box.isChecked() and self.show_attack_box.isChecked():
            self.drawAttackHitbox(c, frame, scale_ratio)

        # FINAL
        self.image_label.setPixmap(QGui.QPixmap.fromImage(ImageQt(frame)))
        # self.image_label.set

    def drawAttackHitbox(self, n: int, frame: Image.Image, scale_ratio: float):
        if not checkCorrectAttackList(self.attack_input.text()):
            return

        attack_data = literal_eval(self.attack_input.text())
        data, flag = None, False
        for data in attack_data:
            if data[0] == n:
                flag = True
                break
        if data is None or flag is False:
            return

        draw = ImageDraw.Draw(frame)
        x, y, w, h = [x * scale_ratio for x in data[2]]
        x = frame.width // 2 + x - w // 2
        y = frame.height // 2 - y - h // 2
        box = [x, y, x + w, y + h]

        if data[1] == 0:
            # DRAW CIRCLE
            draw.ellipse(box, outline='red', width=2)

        elif data[1] == 1:
            # DRAW RECTANGLE
            draw.rectangle(box, outline='red', width=2)

    def what_frame(self, time):
        if time == 0:
            return 0

        delays = literal_eval(f'[0, {self.delays_input.text()[1:]}')

        for x in range(1, len(delays)):
            delays[x] = delays[x] * TICK_RATE + delays[x - 1]

        i = 0
        for i in range(1, len(delays)):
            if delays[i - 1] < time <= delays[i]:
                return i - 1
        return i - 1

    def reset_play(self):
        if self.update_animation.isActive():
            self.play_animation()
        self.play_slider.setValue(0)
        self.frame_show(0)

    @QCore.pyqtSlot()
    def delays_changed(self):
        self.changed = True
        self.reset_play()

        text = self.delays_input.text()
        if checkCorrectList(text):
            self.delays_input.setStyleSheet('')

            time = sum(literal_eval(text))
            self.play_slider.setMaximum(int(time * TICK_RATE))

        else:
            self.delays_input.setStyleSheet('background-color: rgb(255, 0, 0);')

    @QCore.pyqtSlot()
    def attack_frames_changed(self):
        self.changed = True
        self.reset_play()

        text = self.attack_input.text()
        if checkCorrectAttackList(text):
            self.attack_input.setStyleSheet('')
        else:
            self.attack_input.setStyleSheet('background-color: rgb(255, 0, 0);')

    @QCore.pyqtSlot()
    def name_changed(self):
        self.changed = True

        if checkCorrectName(self.name_input.text(), self.tag):
            self.name_input.setStyleSheet('')
        else:
            self.name_input.setStyleSheet('background-color: rgb(255, 0, 0);')

    def closeEvent(self, event):
        if self.hard_close:
            event.accept()
            window.show()
            return

        if not self.changed:
            event.accept()
            window.show()
            return

        close = QW.QMessageBox.question(
            self, "QUIT", "Save Changes?", QW.QMessageBox.Yes | QW.QMessageBox.No | QW.QMessageBox.Cancel)

        if close == QW.QMessageBox.Cancel:
            event.ignore()
            return

        if close == QW.QMessageBox.Yes:
            if not self.isFieldsCorrect():
                event.ignore()
                QW.QMessageBox.question(self, "error", "Can not save. Change red fields", QW.QMessageBox.Ok)
            else:
                self.saveChanges()
                event.accept()
                window.show()
            return

        event.accept()
        window.show()
        return

    def isFieldsCorrect(self):
        if checkCorrectList(self.delays_input.text()) and checkCorrectName(self.name_input.text(), self.tag):
            if self.isattack_box.isChecked():
                return checkCorrectAttackList(self.attack_input.text())
            return True
        return False

    def saveChanges(self):
        animations = window.animations
        key = self.tag

        # getting copy of animation by past name
        animation = animations[tags[key]].copy()

        # deleting previous animation data
        del animations[tags[key]]

        # getting new animation's name
        new_name = self.name_input.text()

        # updating data
        animation['delays'] = literal_eval(self.delays_input.text())
        animation['isAttack'] = True if self.isattack_box.isChecked() else False
        animation['attackFrames'] = literal_eval(self.attack_input.text())

        #
        animations[new_name] = animation
        tags[self.tag] = new_name

        # updating main window
        window.updateAnimationText(self.tag, new_name)

    def add_to_all_delays(self):
        frames = self.delays_input.text()
        if not checkCorrectList(frames):
            return
        frames = [x + DELAYS_ADD_AMOUNT for x in literal_eval(frames)]
        self.delays_input.setText(str(frames))

    def sub_from_all_delays(self):
        frames = self.delays_input.text()
        if not checkCorrectList(frames):
            return
        frames = [x - DELAYS_SUB_AMOUNT for x in literal_eval(frames)]
        self.delays_input.setText(str(frames))

    def add_attack_frame(self):
        global newAttackWindow
        if not checkCorrectAttackList(self.attack_input.text()):
            return
        self.hide()
        newAttackWindow = NewAttackWindow()
        newAttackWindow.show()

    def close_(self):
        self.hard_close = True
        self.close()

    def close_save(self):
        if self.isFieldsCorrect():
            self.saveChanges()
            self.close_()


animationWindow: AnimationWindow
animationWindowInited = False


class NewAttackWindow(QW.QWidget):
    x_input: QW.QSpinBox
    y_input: QW.QSpinBox
    w_input: QW.QSpinBox
    h_input: QW.QSpinBox

    rect_b: QW.QPushButton
    ellipse_b: QW.QPushButton
    accept_b: QW.QPushButton

    frame_input: QW.QSpinBox
    damage_input: QW.QDoubleSpinBox

    image_l: QW.QLabel

    def __init__(self):
        super().__init__()
        uic.loadUi(TEMPLATES_DIR.format('new_attack'), self)

        self.hide_all()
        self.rect_b.show()
        self.ellipse_b.show()

        self.rect_b.clicked.connect(self.s_rect)
        self.ellipse_b.clicked.connect(self.s_ellipse)
        self.accept_b.clicked.connect(self.apply)

        self.shape = None

    def hide_all(self):
        for x in self.findChildren((QW.QSpinBox, QW.QPushButton, QW.QDoubleSpinBox, QW.QLabel)):
            x.hide()

    def show_all(self):
        for x in self.findChildren((QW.QSpinBox, QW.QPushButton, QW.QDoubleSpinBox, QW.QLabel)):
            x.show()

    def s_rect(self):
        self.shape = 1
        self.input_show()

    def s_ellipse(self):
        self.shape = 0
        self.input_show()

    def input_show(self):
        self.show_all()
        self.ellipse_b.hide()
        self.rect_b.hide()

        image = animationWindow.image
        scale_ratio = min(self.image_l.width() / image.width, self.image_l.height() / image.height)
        image = scale(image, scale_ratio)
        self.image_l.setPixmap(QGui.QPixmap.fromImage(ImageQt(image)))

    def closeEvent(self, a0: QGui.QCloseEvent) -> None:
        animationWindow.show()
        a0.accept()

    def apply(self):
        data = (self.x_input.value(), self.y_input.value(), self.w_input.value(), self.h_input.value())
        data = [self.frame_input.value(), self.shape, data, self.damage_input.value()]
        frames = literal_eval(animationWindow.attack_input.text())
        frames.append(data)

        animationWindow.attack_input.setText(str(frames))
        self.close()


newAttackWindow: NewAttackWindow


def checkCorrectList(text, min_len=1):
    try:
        to_test_list = literal_eval(text)
        assert isinstance(to_test_list, list)
        assert len(to_test_list) >= min_len
        for x in to_test_list:
            assert isinstance(x, int) or isinstance(x, float)

    except Exception:
        return False
    return True


def checkCorrectAttackList(text):
    try:
        to_test_list = literal_eval(text)
        assert isinstance(to_test_list, list)
        for x in to_test_list:
            assert isinstance(x, list) or isinstance(x, tuple)

    except Exception:
        return False
    return True


def checkCorrectName(name, tag):
    anims = window.animations
    return name not in anims.keys() or list(anims.keys()).index(name) == tag


def frames_count(file):
    # FINDING VERTICAL BORDERS OF ANIMATION FRAME
    # RETURNS VERTICAL BORDERS AND HEIGHT OF ANIMATION SHEET

    # open image and preparing array
    im = Image.open(file).convert("RGBA")
    data = np.array(im.getdata(), dtype=np.int16)
    h, w = im.height, im.width
    data = data.reshape([h, w, 4])

    # GETTING FRAMES COUNT. MAY BE INACCURATE (maybe, i don't really know)
    frames = 0
    flag = True
    for x in range(w):
        filled = data[0: h, x: x + 1].sum(axis=2, where=(0, 0, 0, 1)).any()
        if filled and flag:
            frames += 1
            flag = False
        elif not filled:
            flag = True

    im.close()
    return frames


def scale(image: Image.Image, ratio):
    width = int(image.width * ratio // image.width * image.width)
    height = int(image.height * ratio // image.height * image.height)
    return image.resize([width, height], Image.BOX)


if __name__ == '__main__':
    app = QW.QApplication(['App', ])
    window = MainWindow()
    window.show()
    app.exec_()
