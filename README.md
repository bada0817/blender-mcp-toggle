# MCP Toggle

[Blender MCP 애드온](https://www.blender.org/lab/mcp-server/)의 브리지 서버를 **단축키 하나(Ctrl+Alt+M)로 켜고 끄는** 작은 Blender 확장입니다.

A tiny Blender extension that toggles the Blender MCP add-on's bridge server with a single shortcut (Ctrl+Alt+M).

## 왜 만들었나

MCP 애드온에는 `blmcp.server_start`와 `blmcp.server_stop` 두 오퍼레이터만 있고, 둘 다 `poll`이 없습니다.
그래서 두 오퍼레이터를 같은 단축키에 각각 지정해도 상태에 따라 하나만 골라 실행되지 않습니다.
이미 실행 중일 때 start가 호출되면 `Server is already running` 에러가 납니다.

이 확장은 서버 상태를 확인한 뒤 알맞은 오퍼레이터를 대신 호출하는 토글 오퍼레이터를 제공합니다.
MCP 애드온의 코드는 전혀 수정하지 않습니다.

## 기능

- **`blmcp_toggle.toggle`** 오퍼레이터 (이름: *Toggle MCP Bridge Server*)
  - 서버가 실행 중이면 `blmcp.server_stop`, 멈춰 있으면 `blmcp.server_start`를 호출합니다.
  - 원본 오퍼레이터를 그대로 호출하므로 환경설정(host/port 등), 타이머 등록, 에러 표시가 원본과 똑같이 동작합니다.
  - MCP 애드온이 꺼져 있으면 비활성화되고 "The MCP add-on is not enabled"가 표시됩니다.
- **Ctrl+Alt+M 단축키 자동 등록** (Window 키맵이라 모든 에디터에서 동작)

## 요구 사항

- Blender 5.1 이상
- [MCP 애드온](https://www.blender.org/lab/mcp-server/) 설치 및 활성화

## 설치

### 방법 1: zip으로 빌드해서 설치

```bash
git clone https://github.com/<user>/<repo>.git mcp_toggle
cd mcp_toggle
blender -b --command extension build
```

Blender에서 **Edit → Preferences → Get Extensions → 오른쪽 위 ⌄ → Install from Disk...** 로 생성된 `mcp_toggle-<버전>.zip`을 선택합니다.

명령줄로 설치할 수도 있습니다.

```bash
blender -b --command extension install-file -r user_default -e mcp_toggle-<버전>.zip
```

### 방법 2: 로컬 저장소로 연결 (개발용)

코드를 고치면 Blender를 다시 시작하거나 애드온을 껐다 켜는 것만으로 반영됩니다.

1. 이 저장소를 클론한 **상위 폴더**를 준비합니다 (예: `~/blender_addons/mcp_toggle`이면 `~/blender_addons`).
2. **Edit → Preferences → Get Extensions → ⌄ → Repositories → `+` → Add Local Repository** 에서 그 상위 폴더를 지정합니다.
3. **Add-ons** 탭에서 *MCP Toggle*을 켭니다.

## 사용법

- **Ctrl+Alt+M** 을 누릅니다.
- 또는 F3 검색에서 *Toggle MCP Bridge Server*를 실행합니다.

상태 표시줄에 `MCP bridge server started` / `MCP bridge server stopped`가 나타납니다.

### 단축키 바꾸기

**Preferences → Keymap** 에서 `blmcp_toggle.toggle`을 검색해 바꾸거나 끌 수 있습니다.
예전에 start/stop을 같은 키에 직접 지정했다면 충돌하지 않도록 그 항목들은 지워 주세요.

## 동작 원리

MCP 애드온의 `mcp_to_blender_server.is_running()`(리스닝 소켓이 있는지 확인)으로 서버 상태를 판단합니다.
애드온 패키지 이름은 설치된 저장소마다 다르기 때문에(예: `bl_ext.user_default.mcp`), 활성화된 애드온 중에서 `mcp_to_blender_server` 모듈을 찾아 사용합니다.

## 주의

Claude Code 같은 MCP 클라이언트가 이 서버로 Blender에 연결돼 있다면, 서버를 멈추는 순간 그 연결도 끊어집니다.

## 라이선스

[GPL-3.0-or-later](LICENSE). Blender 애드온 라이선스 요건과 MCP 애드온의 라이선스를 따릅니다.
