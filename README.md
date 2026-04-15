# Academic Video Downloader and BigBlueButton Parser Pipeline

This repository contains a suite of automation scripts and tools designed to streamline the archiving and offline viewing of academic video streams. It handles both standard DRM-protected multimedia distribution streams and dynamic web conferencing platforms.

## Overview

The project is divided into two primary subsystems:

### 1. BigBlueButton (BBB) Downloader and Multiplexer
An automated pipeline that reconstructs interactive BigBlueButton virtual sessions into standard, highly compatible video files (MKV).
- Captures SVG and PNG presentation slides dynamically from active BBB sessions via Chrome Headless rendering.
- Downmixes and synchronizes webcam audio streams accurately against presentation timeline metadata (`shapes.svg`).
- Compiles thousands of discrete visual frames and audio into an optimized `x264` MKV utilizing a robust single-pass FFmpeg multiplexing strategy.
- Employs a local browser profile bypass to handle authenticated sessions without exposing credentials.

### 2. DRM content handling (N_m3u8DL-RE & Telegram Bot Interface)
A separate layer dedicated to interacting confidently with encrypted HLS/DASH media payloads.
- Interfaces via remote Telegram Bot (`drm_bot.py`), removing the need for manual command-line execution when parsing M3U8/MPD manifests and extraction parameters.
- Incorporates Widevine decryption capabilities combined with multi-threaded downloading provided by `N_m3u8DL-RE`.
- Bundled with internal browser extensions designed to intercept application licenses and playback metadata safely.
- Incorporates automated local tests for Bunny.net endpoints and offline validation.

## Prerequisites

The logic requires specific binary dependencies and utilities to function correctly. Ensure these are present in the core directories before execution:
- `FFmpeg` (Required for multiplexing operations)
- `N_m3u8DL-RE` (Target downloader handler)
- `mp4decrypt`
- Python 3.10+ alongside libraries listed in `requirements.txt`.
- Existing installations of Google Chrome or Microsoft Edge.

## Usage

Each module provides automated batch launch files for streamlined initialization:
- Execute `Lanzar_BBB_Downloader.bat` for an interactive CLI to acquire and multiplex BBB recordings.
- Execute `Lanzar_DRM_Bot.bat` to host the background Telegram polling worker.
- Additional lab and experiment scripts are segregated within the `LAB_DRM` directory.

## Notice

This repository code functions as a personalized abstraction library for educational archiving. Cryptographic components (e.g. Widevine L3 CDMs) and executable binaries are explicitly excluded from this remote repository for security and compliance purposes.
