local utils = require 'mp.utils'

path = debug.getinfo(1,'S').source:match('(.*[/\\])')
server_path = path .. 'main.py'
ipc_socket_path = path .. 'mpv_socket_' .. utils.getpid()

function remove_socket()
    os.remove(ipc_socket_path)
end
mp.set_property("options/input-ipc-server", ipc_socket_path)
mp.register_event("shutdown", remove_socket)

utils.subprocess_detached({args = {'python3', server_path, ipc_socket_path}})

