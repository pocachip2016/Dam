# Step M.4: video-mock-ingest

> GitHub: 미생성 | Milestone: dev-meta-foundation

## 읽어야 할 파일
- `ingest/ingest_local.py` — 기존 이미지 인제스트 패턴
- `ingest/thumbnail_worker.py` — 썸네일 생성 패턴
- `ingest/clip_worker.py` — CLIP 임베딩 생성 패턴
- `plans/dev-meta-foundation/index.json` → decisions.video_ingest

## 배경
현재 Dam은 이미지(jpg/png/gif 등) 전용 파이프라인. 영상(mp4/mkv/mov 등) 인제스트 파이프라인이 없다. 실데이터 전환 전에 mock 파일 1개로 파이프라인 전체를 검증한다.

영상 처리 추가 작업:
1. **프레임 추출** — ffmpeg으로 대표 프레임(썸네일) 추출
2. **썸네일 생성** — 기존 thumbnail_worker.py 재사용 가능
3. **CLIP 임베딩** — 대표 프레임 이미지로 임베딩 생성 (기존 clip_worker 재사용)
4. **메타데이터** — 영상 duration, fps, resolution, codec 추출 (ffprobe)

## 작업

### mock 파일 준비
```bash
# ffmpeg으로 10초짜리 테스트 영상 생성
ffmpeg -f lavfi -i testsrc=duration=10:size=1920x1080:rate=24 \
       -f lavfi -i sine=frequency=440:duration=10 \
       -c:v libx264 -c:a aac \
       /tmp/mock_video.mp4
```
파일을 `dam_data/test/mock_video.mp4`에 배치.

### `ingest/video_worker.py` 작성

```python
VIDEO_EXTS = {'.mp4', '.mkv', '.mov', '.avi', '.m4v', '.ts', '.webm'}

class VideoWorker:
    def __init__(self, conn, dam_data_dir: str):
        ...

    def extract_keyframe(self, video_path: str, thumb_path: str) -> bool:
        # ffmpeg -ss 00:00:01 -i video_path -vframes 1 thumb_path
        # 실패 시 False 반환 (ffmpeg 미설치 등)
        ...

    def extract_video_meta(self, video_path: str) -> dict:
        # ffprobe -v quiet -print_format json -show_format -show_streams
        # → duration, fps, width, height, codec, bitrate
        ...

    def ingest_video(self, file_path: str, realm: str) -> dict:
        # 1. assets INSERT (기존 패턴)
        # 2. asset_storage INSERT
        # 3. keyframe 추출 → thumbnail_path
        # 4. 비디오 메타 → assets.raw_meta (JSONB)
        # 5. 임베딩은 clip_worker에 위임
        ...
```

### `ingest_local.py` 확장
- `IMAGE_EXTS` 와 별도로 `VIDEO_EXTS` 처리 분기 추가
- 영상 파일은 VideoWorker.ingest_video() 호출

### ffmpeg 의존성
`Dockerfile`에 ffmpeg 설치 추가:
```dockerfile
RUN apt-get update && apt-get install -y ffmpeg
```

## Acceptance Criteria
```bash
bash .claude/verify.sh M.4
```
- mock_video.mp4 인제스트 후 `SELECT id, thumbnail_path FROM assets WHERE file_ext='.mp4';` → 1행
- 썸네일 파일 실제 존재 확인
- `SELECT raw_meta->>'duration' FROM assets WHERE file_ext='.mp4';` → 값 존재
- CLIP 임베딩 생성 확인: `SELECT count(*) FROM embeddings e JOIN assets a ON a.id=e.asset_id WHERE a.file_ext='.mp4';`

## 금지사항
- 실 영상 파일(D:\dam_poc_sample 등) 이번 step에서 처리 금지 — mock 1개만
- 영상 전체 프레임 추출 금지 — 대표 프레임(1~3개) 만
- ffmpeg 미설치 환경에서 crash 내지 말고 graceful skip
