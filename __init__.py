# SPDX-License-Identifier: GPL-3.0-or-later

"""
Toggle operator for the MCP add-on's bridge server.

Reads the server state from the MCP add-on's ``mcp_to_blender_server.is_running()``
and calls ``blmcp.server_stop`` or ``blmcp.server_start`` accordingly.
While the server is running, a short status line is drawn in a corner of the 3D viewport.
The MCP add-on itself is not modified.
"""

__all__ = (
    "register",
    "unregister",
)

import sys

import blf  # pylint: disable=import-error
import bpy  # pylint: disable=import-error
from bpy.props import (
    BoolProperty,
    EnumProperty,
)  # pylint: disable=import-error

# Module name of the MCP add-on's server module, without the package prefix.
# The package prefix depends on the repository it's installed in,
# e.g. ``bl_ext.user_default.mcp``.
_SERVER_MODULE_SUFFIX = ".mcp_to_blender_server"


def _server_module_find():
    """
    Return the MCP add-on's server module, or None when the add-on isn't enabled.
    """
    for name, module in tuple(sys.modules.items()):
        if module is None or not name.endswith(_SERVER_MODULE_SUFFIX):
            continue
        if not callable(getattr(module, "is_running", None)):
            continue
        # Only accept the module of an enabled add-on (ignore stale modules after disabling).
        package = name[:-len(_SERVER_MODULE_SUFFIX)]
        if package in bpy.context.preferences.addons:
            return module
    return None


def _server_port(server) -> int | None:
    """
    Return the port the server is listening on, or None when it can't be found.
    """
    # The bound socket is the most accurate source,
    # the preferences may have been changed after the server started.
    sock = getattr(getattr(server, "_state", None), "sock", None)
    if sock is not None:
        try:
            return sock.getsockname()[1]
        except OSError:
            pass
    package = server.__name__[:-len(_SERVER_MODULE_SUFFIX)]
    addon = bpy.context.preferences.addons.get(package)
    return getattr(getattr(addon, "preferences", None), "port", None)


def _operators_registered() -> bool:
    for op in (bpy.ops.blmcp.server_start, bpy.ops.blmcp.server_stop):
        try:
            op.get_rna_type()
        except KeyError:
            return False
    return True


class BLMCP_TOGGLE_OT_toggle(bpy.types.Operator):  # type: ignore[misc]
    bl_idname = "blmcp_toggle.toggle"
    bl_label = "Toggle MCP Bridge Server"
    bl_description = "Start the MCP bridge server if it's stopped, stop it if it's running"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        del context
        if _server_module_find() is None or not _operators_registered():
            cls.poll_message_set("The MCP add-on is not enabled")
            return False
        return True

    def execute(self, context: bpy.types.Context) -> set[str]:
        server = _server_module_find()
        if server.is_running():
            op, action = bpy.ops.blmcp.server_stop, "stopped"
        else:
            op, action = bpy.ops.blmcp.server_start, "started"

        # Errors reported by the called operator are raised as `RuntimeError`.
        try:
            result = op()
        except RuntimeError as ex:
            # The message is already prefixed with "Error: ", don't repeat it.
            self.report({"ERROR"}, str(ex).strip().removeprefix("Error: "))
            return {"CANCELLED"}
        if "FINISHED" not in result:
            return {"CANCELLED"}

        _view3d_redraw_all(context)
        self.report({"INFO"}, "MCP bridge server {:s}".format(action))
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Viewport status overlay.
#
# The server state is read while drawing, there is no timer polling it.
# The toggle operator redraws the viewports, other state changes
# (e.g. the MCP preferences buttons) show up on the next viewport redraw.

def _view3d_redraw_all(context: bpy.types.Context) -> None:
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _preferences_update(self, context: bpy.types.Context) -> None:
    del self
    _view3d_redraw_all(context)


class _MCPTogglePreferences(bpy.types.AddonPreferences):  # type: ignore[misc]
    bl_idname = __package__

    show_overlay: BoolProperty(  # type: ignore[valid-type]
        name="Show Status in Viewport",
        description="Show the server port in a corner of the 3D viewport while the server is running",
        default=True,
        update=_preferences_update,
    )
    overlay_corner: EnumProperty(  # type: ignore[valid-type]
        name="Corner",
        items=(
            ("BOTTOM_LEFT", "Bottom Left", ""),
            ("BOTTOM_RIGHT", "Bottom Right", ""),
        ),
        default="BOTTOM_RIGHT",
        update=_preferences_update,
    )

    def draw(self, context: bpy.types.Context) -> None:
        del context
        layout = self.layout
        layout.prop(self, "show_overlay")
        row = layout.row()
        row.active = self.show_overlay
        row.prop(self, "overlay_corner")


def _overlay_draw() -> None:
    context = bpy.context
    addon = context.preferences.addons.get(__package__)
    if addon is None:
        return
    prefs = addon.preferences
    if not prefs.show_overlay:
        return
    # Follow the viewport's overlay toggle like Blender's own overlays.
    if not context.space_data.overlay.show_overlays:
        return
    server = _server_module_find()
    if server is None or not server.is_running():
        return

    port = _server_port(server)
    if port is None:
        text = "MCP server running"
    else:
        text = "MCP server running \u00b7 port {:d}".format(port)

    region = context.region
    scale = context.preferences.system.ui_scale
    font_id = 0
    blf.size(font_id, 11.0 * scale)
    text_width, _text_height = blf.dimensions(font_id, text)
    margin = 10.0 * scale

    # With region overlap the toolbar & sidebar are drawn over this region, keep clear of them.
    inset_left = inset_right = 0
    if context.preferences.system.use_region_overlap:
        for other in context.area.regions:
            if other.type not in {"TOOLS", "UI"} or other.width <= 1:
                continue
            if other.alignment == "RIGHT":
                inset_right = max(inset_right, other.width)
            else:
                inset_left = max(inset_left, other.width)

    if prefs.overlay_corner == "BOTTOM_LEFT":
        x = inset_left + margin
    else:
        x = region.width - inset_right - margin - text_width

    blf.color(font_id, 0.55, 0.9, 0.55, 0.9)
    blf.enable(font_id, blf.SHADOW)
    blf.shadow(font_id, 3, 0.0, 0.0, 0.0, 0.7)
    blf.shadow_offset(font_id, 1, -1)
    blf.position(font_id, x, margin, 0.0)
    blf.draw(font_id, text)
    blf.disable(font_id, blf.SHADOW)


_draw_handle = None


def _overlay_register() -> None:
    global _draw_handle
    _draw_handle = bpy.types.SpaceView3D.draw_handler_add(_overlay_draw, (), "WINDOW", "POST_PIXEL")


def _overlay_unregister() -> None:
    global _draw_handle
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None
    _view3d_redraw_all(bpy.context)


_classes = (
    _MCPTogglePreferences,
    BLMCP_TOGGLE_OT_toggle,
)

# Keymap items added by this add-on, removed on unregister.
_keymap_items: list[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem]] = []


def _keymap_register() -> None:
    # The add-on key configuration is None in background mode.
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return
    # The "Window" keymap works in every editor.
    km = kc.keymaps.new(name="Window", space_type="EMPTY")
    kmi = km.keymap_items.new(BLMCP_TOGGLE_OT_toggle.bl_idname, "M", "PRESS", ctrl=True, alt=True)
    _keymap_items.append((km, kmi))


def _keymap_unregister() -> None:
    for km, kmi in _keymap_items:
        km.keymap_items.remove(kmi)
    _keymap_items.clear()


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)
    _keymap_register()
    _overlay_register()


def unregister() -> None:
    _overlay_unregister()
    _keymap_unregister()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
