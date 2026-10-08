# SPDX-License-Identifier: GPL-3.0-or-later

"""
Toggle operator for the MCP add-on's bridge server.

Reads the server state from the MCP add-on's ``mcp_to_blender_server.is_running()``
and calls ``blmcp.server_stop`` or ``blmcp.server_start`` accordingly.
The MCP add-on itself is not modified.
"""

__all__ = (
    "register",
    "unregister",
)

import sys

import bpy  # pylint: disable=import-error

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
        del context
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

        self.report({"INFO"}, "MCP bridge server {:s}".format(action))
        return {"FINISHED"}


_classes = (
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


def unregister() -> None:
    _keymap_unregister()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
