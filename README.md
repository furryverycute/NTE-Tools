# NTE Tool Python Demo v41

Neverness To Everness 편의 도구입니다.

## 포함 기능

- 별미 카페 자동화
- 장착 시뮬레이터
- 가방 OCR 스캔 및 추천 장착
- 최종 스펙 계산
- GitHub 릴리스 업데이트 확인

## 최초 설정

```bat
setup.bat
```

Python·앱·스캔 의존성, 포터블 Tesseract를 한 번에 준비합니다.
`requirements.txt`, `requirements-scan.txt`가 처음 실행되었거나 변경되면 자동으로 다시 설치합니다.
기존 Tesseract 폴더를 지정하려면 다음처럼 실행합니다.

```bat
setup.bat "C:\Program Files\Tesseract-OCR"
```

## 실행

```bat
run_demo.bat
```

`run_demo.bat`도 requirements 변경을 감지해 실행 전에 자동 동기화합니다.

## 릴리스 파일 생성

```bat
build_release_assets.bat
```

완료되면 `release` 폴더에 두 파일이 생성됩니다.

- `NTE-Tool-v41-installer.exe`: 설치형 exe
- `NTE-Tool-v41-portable.zip`: 포터블 배포 파일

설정 탭의 업데이트 기능은 GitHub 릴리스에서 `installer/setup/install`이 들어간 exe/msi를 설치형으로, `portable`이 들어간 zip/exe를 포터블로 인식합니다.

## 포터블 Tesseract 구조

```txt
tools\tesseract\tesseract.exe
tools\tesseract\*.dll
tools\tesseract\tessdata\eng.traineddata
tools\tesseract\tessdata\kor.traineddata
```
