from __future__ import annotations

import os
from datetime import datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from freebuds.core.client import DeviceSnapshot  # noqa: E402
from freebuds.core.commands import CMD_ANC  # noqa: E402
from freebuds.core.models import (
    AdvancedSettings,
    AncState,
    BatteryState,
    DeviceInfo,
)  # noqa: E402
from freebuds.core.protocol import encode_frame, parse_frame  # noqa: E402
from freebuds.ui.main_window import MainWindow  # noqa: E402
from freebuds.ui.widgets import AncPanel, FeaturesPanel  # noqa: E402


@pytest.fixture(scope="module")
def app() -> QApplication:
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    return instance


def test_main_window_starts_and_renders_snapshot(app, tmp_path) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.show()
    app.processEvents()

    assert window.windowTitle() == "FreeBuds Client"
    assert window.connection_pill.text() == "Desconectado"
    assert window.battery_panel.global_card.value_label.text() == "—"
    assert window.anc_panel.mode_label.text() == "Sem dados"

    info = DeviceInfo(
        hardware_version="HL1SAKM2_Ver.A",
        software_version="HarmonyOS 7.0.0.350",
        submodel="BTFT0023-00016D",
        model="BTFT0023",
    )
    battery = BatteryState(
        global_level=83,
        left=83,
        right=83,
        case=69,
        charging=True,
        charging_flags=b"\x01\x01\x01",
        parameters={1: bytes([83]), 2: bytes([83, 83, 69])},
    )
    anc = AncState(
        mode_code=1,
        mode="cancellation",
        level_code=3,
        level="dynamic",
        parameters={1: bytes([3, 1])},
    )
    snapshot = DeviceSnapshot(
        info=info,
        battery=battery,
        anc=anc,
        notifications=[],
        warnings=[],
        parser_issues=[],
        timestamp=datetime(2026, 10, 21, 18, 30, 0),
        channel=1,
    )

    window.battery_panel.update_battery(snapshot.battery)
    window.anc_panel.update_anc(snapshot.anc)
    window.details_panel.update_info(snapshot.info, snapshot.channel, snapshot.timestamp)
    app.processEvents()

    assert window.battery_panel.global_card.value_label.text() == "83%"
    assert window.battery_panel.case_card.value_label.text() == "69%"
    assert window.battery_panel.charging_label.isVisible() is True
    assert window.battery_panel.flags_label.text() == "Flags de carga: 01 01 01"
    assert window.anc_panel.mode_label.text() == "Cancelamento"
    assert window.anc_panel.level_label.text() == "Nível: Dinâmico"
    assert window.anc_panel.mode_buttons[1].isChecked() is True
    assert window.anc_panel.mode_buttons[0].isChecked() is False
    assert window.details_panel._values["channel"].text() == "1"
    assert window.details_panel._values["model"].text() == "BTFT0023"

    window.shutdown()
    window._force_quit = True
    window.close()


def test_anc_unknown_level_is_not_invented(app, tmp_path) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    anc = AncState(
        mode_code=2,
        mode="awareness",
        level_code=3,
        level=None,
        parameters={1: bytes([3, 2])},
    )
    window.anc_panel.update_anc(anc)
    app.processEvents()

    assert window.anc_panel.mode_label.text() == "Transparência"
    assert "código 3" in window.anc_panel.level_label.text()
    assert "não mapeado" in window.anc_panel.level_label.text()
    assert window.anc_panel.mode_buttons[2].isChecked() is True

    window.shutdown()
    window._force_quit = True
    window.close()


def test_anc_normal_does_not_show_padding_level_code(app, tmp_path) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    anc = AncState(
        mode_code=0,
        mode="normal",
        level_code=0,
        level=None,
        parameters={1: bytes([0, 0]), 2: bytes([5])},
    )
    window.anc_panel.update_anc(anc)
    app.processEvents()

    assert window.anc_panel.mode_label.text() == "Normal"
    assert window.anc_panel.level_label.text() == "Nível: —"
    assert window.anc_panel.mode_buttons[0].isChecked() is True

    window.shutdown()
    window._force_quit = True
    window.close()


def test_unknown_notifications_are_deduplicated(app, tmp_path) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.log_view.clear()
    frame = parse_frame(encode_frame(0x2B25, {1: b"\x01", 2: b"\x00"}))
    changed = parse_frame(encode_frame(0x2B25, {1: b"\x02", 2: b"\x00"}))

    window._handle_notification(frame)
    window._handle_notification(frame)
    assert window.log_view.toPlainText().count("Notificação 2B 25") == 1

    window._handle_notification(changed)
    assert window.log_view.toPlainText().count("Notificação 2B 25") == 2

    window.shutdown()
    window._force_quit = True
    window.close()


def test_activity_log_keeps_message(app, tmp_path) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.log_view.clear()
    window.log_view.log("teste de atividade", "ok")
    app.processEvents()

    assert "teste de atividade" in window.log_view.toPlainText()

    window.shutdown()
    window._force_quit = True
    window.close()


def test_anc_panel_emits_mode_and_level_actions(app) -> None:
    panel = AncPanel()
    panel.show()
    panel.set_enabled(True)
    modes: list[int] = []
    levels: list[int] = []
    panel.mode_requested.connect(modes.append)
    panel.level_requested.connect(levels.append)

    anc = AncState(
        mode_code=1,
        mode="cancellation",
        level_code=3,
        level="dynamic",
        parameters={1: bytes([3, 1])},
    )
    panel.update_anc(anc)
    app.processEvents()

    assert panel.mode_buttons[1].isChecked() is True
    assert not panel.cancellation_levels.isHidden()
    assert panel.cancellation_levels.isVisible() is True
    assert panel.level_buttons[(1, 3)].isChecked() is True

    panel.mode_buttons[2].click()
    assert modes == [2]
    panel.level_buttons[(1, 2)].click()
    assert levels == [2]

    panel.set_enabled(False)
    panel.mode_buttons[0].click()
    assert modes == [2]

    panel.close()


def test_anc_panel_adaptive_mode_and_level_slider(app) -> None:
    panel = AncPanel()
    panel.show()
    panel.set_enabled(True)
    requests: list[int] = []
    adaptive_requests: list[bool] = []
    panel.adaptive_level_requested.connect(requests.append)
    panel.adaptive_requested.connect(lambda: adaptive_requests.append(True))

    panel.update_anc(
        AncState(
            mode_code=2,
            mode="awareness",
            level_code=4,
            level="adaptive",
            adaptive_level=5,
            parameters={1: bytes([4, 2]), 2: bytes([5])},
        )
    )
    app.processEvents()

    assert panel.mode_label.text() == "Reconhecimento adaptável"
    assert panel.level_label.text() == "Nível: 6 de 11 · padrão"
    assert panel.adaptive_chip_shortcut.isChecked() is True
    assert panel.adaptive_controls.isVisible() is True
    assert panel.awareness_levels.isVisible() is False
    assert panel.adaptive_slider.value() == 6
    assert panel.adaptive_value_label.text() == "6 de 11 · padrão"
    assert panel.adaptive_slider.isEnabled() is True

    panel.adaptive_slider.setValue(11)
    app.processEvents()
    assert requests == [10]

    panel.update_anc(
        AncState(
            mode_code=2,
            mode="awareness",
            level_code=2,
            level="normal",
            parameters={1: bytes([2, 2])},
        )
    )
    app.processEvents()
    assert panel.awareness_levels.isVisible() is True
    panel.adaptive_chip_shortcut.click()
    app.processEvents()
    assert adaptive_requests == [True]

    panel.close()


def test_anc_panel_exposes_unknown_level_without_button(app) -> None:
    panel = AncPanel()
    panel.show()
    panel.set_enabled(True)
    panel.update_anc(
        AncState(
            mode_code=2,
            mode="awareness",
            level_code=3,
            level=None,
            parameters={1: bytes([3, 2])},
        )
    )
    app.processEvents()

    assert panel.awareness_levels.isVisible() is True
    assert panel.unknown_level_label.isVisible() is True
    assert "nível 3" in panel.unknown_level_label.text()
    assert all(
        not button.isChecked()
        for (mode_code, level_code), button in panel.level_buttons.items()
        if mode_code == 2
    )
    panel.close()


def test_notification_is_logged_without_rewriting_polled_snapshot(app, tmp_path) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.log_view.clear()
    snapshot = DeviceSnapshot(
        info=DeviceInfo(model="BTFT0023"),
        battery=None,
        anc=AncState(
            mode_code=1,
            mode="cancellation",
            level_code=3,
            level="dynamic",
        ),
        notifications=[],
        warnings=[],
        parser_issues=[],
        timestamp=datetime(2026, 10, 21, 18, 30, 0),
        channel=1,
    )
    frame = parse_frame(encode_frame(CMD_ANC, {1: bytes([0, 0])}))

    window._handle_notification(frame)
    app.processEvents()

    assert snapshot.anc is not None
    assert snapshot.anc.mode == "cancellation"
    assert "Notificação de ANC: Normal" in window.log_view.toPlainText()
    assert "código 0" not in window.log_view.toPlainText()

    window.shutdown()
    window._force_quit = True
    window.close()


class _FakeWorker(QObject):
    action_failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.mode_calls: list[int] = []
        self.level_calls: list[tuple[int, int]] = []
        self.adaptive_calls: list[int] = []
        self.feature_calls: list[tuple[str, object]] = []

    def set_anc_mode(self, mode_code: int) -> None:
        self.mode_calls.append(mode_code)

    def set_anc_level(self, mode_code: int, level_code: int) -> None:
        self.level_calls.append((mode_code, level_code))

    def set_anc_adaptive_level(self, level_code: int) -> None:
        self.adaptive_calls.append(level_code)

    def set_sound_profile(self, profile_id: int) -> None:
        self.feature_calls.append(("sound_profile", profile_id))

    def set_spatial_mode(self, mode_code: int) -> None:
        self.feature_calls.append(("spatial_mode", mode_code))

    def set_adaptive_volume(self, enabled: bool) -> None:
        self.feature_calls.append(("adaptive_volume", enabled))

    def set_conversation_awareness(self, enabled: bool) -> None:
        self.feature_calls.append(("conversation_awareness", enabled))

    def set_one_earbud_anc(self, enabled: bool) -> None:
        self.feature_calls.append(("one_earbud_anc", enabled))

    def set_head_control(self, enabled: bool | None = None) -> None:
        self.feature_calls.append(("head_control", enabled))

    def set_head_action(self, field: int, action: int) -> None:
        self.feature_calls.append(("head_action", (field, action)))

    def set_wear_detection(self, enabled: bool) -> None:
        self.feature_calls.append(("wear_detection", enabled))

    def set_sound_quality(self, value: int) -> None:
        self.feature_calls.append(("sound_quality", value))

    def set_low_latency(self, enabled: bool) -> None:
        self.feature_calls.append(("low_latency", enabled))

    def set_press_hold(self, side: str, action: int) -> None:
        self.feature_calls.append(("press_hold", (side, action)))

    def set_pinch_hold(self, side: str, action: int) -> None:
        self.feature_calls.append(("pinch_hold", (side, action)))

    def set_double_tap(self, left: int, right: int) -> None:
        self.feature_calls.append(("double_tap", (left, right)))

    def set_triple_tap(self, side: str, action: int) -> None:
        self.feature_calls.append(("triple_tap", (side, action)))


def test_main_window_enqueues_anc_actions_and_blocks_duplicates(app, tmp_path) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.show()
    snapshot = DeviceSnapshot(
        info=DeviceInfo(model="BTFT0023"),
        battery=None,
        anc=AncState(
            mode_code=1,
            mode="cancellation",
            level_code=3,
            level="dynamic",
            parameters={1: bytes([3, 1])},
        ),
        notifications=[],
        warnings=[],
        parser_issues=[],
        timestamp=datetime(2026, 10, 21, 18, 30, 0),
        channel=1,
    )
    worker = _FakeWorker()
    worker.action_failed.connect(window._on_action_failed)
    window._worker = worker  # type: ignore[assignment]
    window._session_connected = True
    window._last_snapshot = snapshot
    window.anc_panel.update_anc(snapshot.anc)
    window._update_controls()
    app.processEvents()

    assert window.anc_panel.mode_buttons[2].isEnabled() is True
    window.anc_panel.mode_buttons[2].click()
    assert worker.mode_calls == []
    assert worker.level_calls == [(2, 2)]
    assert window._anc_busy is True
    assert window.anc_panel.mode_buttons[0].isEnabled() is False

    window.anc_panel.mode_buttons[0].click()
    assert worker.mode_calls == []
    assert worker.level_calls == [(2, 2)]

    worker.action_failed.emit("falha simulada")
    assert window._anc_busy is False
    app.processEvents()
    assert window.anc_panel.mode_buttons[0].isEnabled() is True

    window.anc_panel.level_buttons[(1, 2)].click()
    assert worker.level_calls == [(2, 2), (1, 2)]

    window._worker = None
    window.shutdown()
    window._force_quit = True
    window.close()


def test_main_window_enqueues_adaptive_actions(app, tmp_path) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.show()
    transparency = AncState(
        mode_code=2,
        mode="awareness",
        level_code=2,
        level="normal",
        parameters={1: bytes([2, 2])},
    )
    snapshot = DeviceSnapshot(
        info=DeviceInfo(model="BTFT0023"),
        battery=None,
        anc=transparency,
        notifications=[],
        warnings=[],
        parser_issues=[],
        timestamp=datetime(2026, 10, 21, 18, 30, 0),
        channel=1,
    )
    worker = _FakeWorker()
    worker.action_failed.connect(window._on_action_failed)
    window._worker = worker  # type: ignore[assignment]
    window._session_connected = True
    window._last_snapshot = snapshot
    window.anc_panel.update_anc(snapshot.anc)
    window._update_controls()
    app.processEvents()

    window.anc_panel.adaptive_chip_shortcut.click()
    assert worker.level_calls == [(2, 4)]
    assert window._anc_busy is True

    adaptive = AncState(
        mode_code=2,
        mode="awareness",
        level_code=4,
        level="adaptive",
        adaptive_level=5,
        parameters={1: bytes([4, 2]), 2: bytes([5])},
    )
    window._last_snapshot = DeviceSnapshot(
        info=DeviceInfo(model="BTFT0023"),
        battery=None,
        anc=adaptive,
        notifications=[],
        warnings=[],
        parser_issues=[],
        timestamp=datetime(2026, 10, 21, 18, 31, 0),
        channel=1,
    )
    window._anc_busy = False
    window.anc_panel.update_anc(adaptive)
    window._update_controls()
    app.processEvents()

    window.anc_panel.adaptive_slider.setValue(11)
    assert worker.adaptive_calls == [10]
    assert window._anc_busy is True

    maximum = AncState(
        mode_code=2,
        mode="awareness",
        level_code=4,
        level="adaptive",
        adaptive_level=10,
        parameters={1: bytes([4, 2]), 2: bytes([10])},
    )
    window._last_snapshot = DeviceSnapshot(
        info=DeviceInfo(model="BTFT0023"),
        battery=None,
        anc=maximum,
        notifications=[],
        warnings=[],
        parser_issues=[],
        timestamp=datetime(2026, 10, 21, 18, 32, 0),
        channel=1,
    )
    window._anc_busy = False
    window.anc_panel.update_anc(maximum)
    window._update_controls()
    app.processEvents()

    window.anc_panel.mode_buttons[2].click()
    assert worker.mode_calls == []
    assert worker.level_calls == [(2, 4), (2, 2)]

    window._worker = None
    window.shutdown()
    window._force_quit = True
    window.close()


def test_features_panel_renders_and_updates_advanced(app) -> None:
    panel = FeaturesPanel()
    panel.show()
    panel.set_enabled(True)

    assert panel.tabs.count() == 3
    assert panel.tabs.tabText(0) == "Áudio"
    assert panel.tabs.tabText(1) == "Gestos"
    assert panel.tabs.tabText(2) == "Conexão"

    data = AdvancedSettings(
        sound_profile_id=5,
        custom_eq=b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A",
        custom_name="Meu Som",
        spatial_mode=1,
        spatial_effect=2,
        adaptive_volume=True,
        conversation_awareness=False,
        head_control=True,
        head_nod_action=1,
        head_shake_action=2,
        wear_detection=True,
        multipoint=True,
        sound_quality=1,
        low_latency=True,
        one_earbud_anc=True,
        press_hold_left=0x0A,
        press_hold_right=0xFF,
        pinch_hold_left=0x06,
        pinch_hold_right=0x06,
        double_tap_left=0x01,
        double_tap_right=0xFF,
        triple_tap_left=0x07,
        triple_tap_right=0x02,
        swipe_up=0x02,
        swipe_down=0x00,
    )
    panel.update_advanced(data)
    app.processEvents()

    assert panel.sound_profile_label.text() == "Equilibrado"
    assert panel.spatial_effect_label.text() == "Efeito: Cinema"
    assert panel.adaptive_volume_switch.isChecked() is True
    assert panel.conversation_switch.isChecked() is False
    assert panel.head_switch.isChecked() is True
    assert panel.latency_switch.isChecked() is True
    assert panel.wear_switch.isChecked() is True
    assert panel.one_earbud_switch.isChecked() is True
    assert "Ativada" in panel.multipoint_label.text()
    assert "Priorizar qualidade" in panel.codec_label.text()
    assert panel.press_left.currentData() == 0x0A
    assert panel.press_right.currentData() == 0xFF
    assert panel.pinch_left.currentData() == 0x06
    assert panel.double_left.currentData() == 0x01
    assert panel.double_right.currentData() == 0xFF
    assert panel.triple_left.currentData() == 0x07
    assert panel.triple_right.currentData() == 0x02
    assert "Cima: Ajustar volume" in panel.swipe_label.text()
    assert "Baixo: Nenhum" in panel.swipe_label.text()

    panel.close()


def test_features_panel_emits_actions(app) -> None:
    panel = FeaturesPanel()
    panel.show()
    panel.set_enabled(True)
    actions: list[tuple[str, object]] = []
    panel.action_requested.connect(lambda action, val: actions.append((action, val)))

    # Alterna o switch de volume adaptável
    panel.adaptive_volume_switch.click()
    assert ("adaptive_volume", True) in actions

    # Alterna o switch de reconhecimento de conversa
    panel.conversation_switch.click()
    assert ("conversation_awareness", True) in actions

    # Clica no chip de modo espacial (modo 1)
    panel.spatial_chips._buttons[1].click()
    assert ("spatial_mode", 1) in actions

    # Clica no chip de perfil (modo 2 - Graves)
    panel.sound_chips._buttons[2].click()
    assert ("sound_profile", 2) in actions

    panel.close()


def test_main_window_dispatches_feature_actions_to_worker(app, tmp_path) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.show()

    worker = _FakeWorker()
    worker.action_failed.connect(window._on_action_failed)
    window._worker = worker  # type: ignore[assignment]
    window._session_connected = True
    window._last_snapshot = DeviceSnapshot(
        info=DeviceInfo(model="BTFT0023"),
        battery=None,
        anc=None,
        notifications=[],
        warnings=[],
        parser_issues=[],
        timestamp=datetime(2026, 10, 21, 18, 30, 0),
        channel=1,
        advanced=AdvancedSettings(sound_profile_id=5),
    )
    window._update_controls()
    app.processEvents()

    # Dispara ação de sound_profile
    window.features_panel.action_requested.emit("sound_profile", 2)
    assert ("sound_profile", 2) in worker.feature_calls
    assert window._anc_busy is True

    window._anc_busy = False
    window.features_panel.action_requested.emit("adaptive_volume", True)
    assert ("adaptive_volume", True) in worker.feature_calls

    window._worker = None
    window.shutdown()
    window._force_quit = True
    window.close()


def test_main_window_navigation_switches_pages(app, tmp_path) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window.show()
    app.processEvents()
    assert window.pages.currentWidget() is window.overview_page

    window._select_page("audio")
    app.processEvents()
    assert window.pages.currentWidget() is window.features_page
    assert window.features_panel.tabs.currentIndex() == 0
    assert window.page_title.text() == "Áudio"
    assert window.nav_buttons["audio"].isChecked() is True

    window._select_page("gestures")
    app.processEvents()
    assert window.features_panel.tabs.currentIndex() == 1

    window._select_page("connection")
    app.processEvents()
    assert window.features_panel.tabs.currentIndex() == 2

    window._select_page("diagnostics")
    app.processEvents()
    assert window.pages.currentWidget() is window.diagnostics_page
    assert window.page_title.text() == "Diagnóstico"

    window._select_page("overview")
    app.processEvents()
    assert window.pages.currentWidget() is window.overview_page
    assert window.nav_buttons["overview"].isChecked() is True

    window.shutdown()
    window._force_quit = True
    window.close()


def test_overview_quick_tiles_reflect_advanced(app, tmp_path) -> None:
    window = MainWindow(settings_path=tmp_path / "settings.json")
    window._update_quick_tiles(
        AdvancedSettings(
            sound_profile_id=5,
            spatial_mode=1,
            head_control=True,
            wear_detection=False,
        )
    )
    app.processEvents()

    assert window.quick_tiles["sound"].value_label.text() == "Equilibrado"
    assert (
        window.quick_tiles["spatial"].value_label.text()
        == "Acompanhamento da cabeça"
    )
    assert window.quick_tiles["head"].value_label.text() == "Ativado"
    assert window.quick_tiles["wear"].value_label.text() == "Desativada"

    window._update_quick_tiles(None)
    for tile in window.quick_tiles.values():
        assert tile.value_label.text() == "—"

    window.shutdown()
    window._force_quit = True
    window.close()

