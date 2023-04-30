# mpv remote server
A server that allow user to control [mpv](https://mpv.io/) from an remote device.
This project is meant to be used with this [Android app](https://github.com/orchidae/mpv-remote-app).
# Installation
Clone the repository to your `mpv/scripts` directory, and the server should load automatically.
# How it works
The server is started with mpv, and periodically advertises itself within the local network.
Once an Android remote receive the advertisement and establish connection with the host, the server will simply retransmit commands to the mpv's IPC socket, and send response from the socket back to the Android remote.
The system was designed with simplicity in mind, the Android remote should automatically connect to the server without the need to input host IP manually.
# Security concerns
The IPC socket mechanism of mpv is by definition not secure, and while I attempted to make the remote connection somewhat safe, I am by no mean a cyber-security expert.
I developped this for personnal usage. **Use it at your own risks!**
