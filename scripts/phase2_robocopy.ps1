# Phase 2 로컬 샘플 복사 스크립트
# 실행: PowerShell에서 .\scripts\phase2_robocopy.ps1
# 소스: \\designfs.ktalpha.com\DESIGNFS\디자인파트\
# 대상: D:\dam_analysis\poc_sample\
# 로그: D:\dam_analysis\poc_sample\_robocopy.log
# 참고: phase2_sample_plan.md — CORE ~31 GB, PSD/PSB/._*/"~$*" 제외

$BASE_SRC = '\\designfs.ktalpha.com\DESIGNFS\디자인파트'
$BASE_DST = 'D:\dam_analysis\poc_sample'
$LOG_FILE = "$BASE_DST\_robocopy.log"

# 대상 루트 생성
New-Item -ItemType Directory -Force -Path $BASE_DST | Out-Null
Write-Host "=== Phase 2 robocopy 시작: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan
"=== Phase 2 robocopy 시작: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -Append $LOG_FILE

function Copy-Dam {
    param(
        [string]$Src,
        [string]$Dst,
        [string]$Label
    )
    Write-Host "`n[$Label]" -ForegroundColor Yellow
    Write-Host "  $Src" -ForegroundColor Gray
    Write-Host "→ $Dst" -ForegroundColor Gray

    robocopy $Src $Dst `
        /E /COPY:DAT `
        /XF *.psd *.psb *.db *.ds_store *.lnk *.ini *.tmp Thumbs.db '._*' '~$*' `
        /MT:8 /R:2 /W:5 `
        /LOG+:$LOG_FILE /NP /NDL

    # robocopy exit code 0-7: 정상 (비트마스크). 8이상은 오류.
    if ($LASTEXITCODE -gt 7) {
        Write-Warning "  오류 (exit $LASTEXITCODE): $Label"
    } else {
        Write-Host "  완료 (exit $LASTEXITCODE)" -ForegroundColor Green
    }
}

# ================================================================
# 섹션 1: 전체 탑레벨 포함 (CORE ≤ 0.1 GB — 6개)
# ================================================================
Write-Host "`n### 섹션 1: 전체 탑레벨 (6개) ###" -ForegroundColor Cyan

Copy-Dam "$BASE_SRC\12.쇼핑 플러스"   "$BASE_DST\12.쇼핑 플러스"   "12.쇼핑 플러스"
Copy-Dam "$BASE_SRC\13.브랜드제휴홈"  "$BASE_DST\13.브랜드제휴홈"  "13.브랜드제휴홈"
Copy-Dam "$BASE_SRC\17.뮤직홈_재작업" "$BASE_DST\17.뮤직홈_재작업" "17.뮤직홈_재작업"
Copy-Dam "$BASE_SRC\32.다이렉트TV샵"  "$BASE_DST\32.다이렉트TV샵"  "32.다이렉트TV샵"
Copy-Dam "$BASE_SRC\34.제휴홈"        "$BASE_DST\34.제휴홈"        "34.제휴홈"
Copy-Dam "$BASE_SRC\35. 혜택+"        "$BASE_DST\35. 혜택+"        "35.혜택+"

# ================================================================
# 섹션 2: 최소 CORE 서브폴더 1개씩 (18개 탑레벨)
# ================================================================
Write-Host "`n### 섹션 2: 최소 CORE 서브폴더 (18개) ###" -ForegroundColor Cyan

Copy-Dam "$BASE_SRC\00. 디자인파트_관리\13_AI디자인" `
         "$BASE_DST\00. 디자인파트_관리\13_AI디자인" `
         "00 / 13_AI디자인"

Copy-Dam "$BASE_SRC\01. olleh tv 운영디자인 가이드\01_GUX_가이드" `
         "$BASE_DST\01. olleh tv 운영디자인 가이드\01_GUX_가이드" `
         "01 / 01_GUX_가이드"

Copy-Dam "$BASE_SRC\04. 디자인소스(무료및보정)\00_올레TV프로모션 자료 공유" `
         "$BASE_DST\04. 디자인소스(무료및보정)\00_올레TV프로모션 자료 공유" `
         "04 / 00_올레TV프로모션 자료 공유"

Copy-Dam "$BASE_SRC\05_리서치자료\02_경쟁사 벤치마킹" `
         "$BASE_DST\05_리서치자료\02_경쟁사 벤치마킹" `
         "05 / 02_경쟁사 벤치마킹"

Copy-Dam "$BASE_SRC\06. FONT\신규폰트_2025" `
         "$BASE_DST\06. FONT\신규폰트_2025" `
         "06 / 신규폰트_2025"

Copy-Dam "$BASE_SRC\07. 최근작업물_공유\유채은_최근작업물" `
         "$BASE_DST\07. 최근작업물_공유\유채은_최근작업물" `
         "07 / 유채은_최근작업물"

Copy-Dam "$BASE_SRC\08. 팀프로젝트\20191205_광고리워드" `
         "$BASE_DST\08. 팀프로젝트\20191205_광고리워드" `
         "08 / 20191205_광고리워드"

Copy-Dam "$BASE_SRC\09. 백업_종료된운영\24.TVshop" `
         "$BASE_DST\09. 백업_종료된운영\24.TVshop" `
         "09 / 24.TVshop"

Copy-Dam "$BASE_SRC\10.올레닷컴_홈페이지\01_이벤트배너 운영 업무" `
         "$BASE_DST\10.올레닷컴_홈페이지\01_이벤트배너 운영 업무" `
         "10 / 01_이벤트배너 운영 업무"

Copy-Dam "$BASE_SRC\14.WEB_3.0\00_메타" `
         "$BASE_DST\14.WEB_3.0\00_메타" `
         "14 / 00_메타"

Copy-Dam "$BASE_SRC\15. ICP_론칭준비\자료" `
         "$BASE_DST\15. ICP_론칭준비\자료" `
         "15 / 자료"

Copy-Dam "$BASE_SRC\16.FAST채널\04_산출물" `
         "$BASE_DST\16.FAST채널\04_산출물" `
         "16 / 04_산출물"

Copy-Dam "$BASE_SRC\18.키즈랜드\2025" `
         "$BASE_DST\18.키즈랜드\2025" `
         "18 / 2025"

Copy-Dam "$BASE_SRC\27.아이프레임\2025" `
         "$BASE_DST\27.아이프레임\2025" `
         "27 / 2025"

Copy-Dam "$BASE_SRC\29.GTM\@디자인산출물" `
         "$BASE_DST\29.GTM\@디자인산출물" `
         "29 / @디자인산출물"

Copy-Dam "$BASE_SRC\30.기가지니\01_가이드" `
         "$BASE_DST\30.기가지니\01_가이드" `
         "30 / 01_가이드"

Copy-Dam "$BASE_SRC\31.전사\인사팀" `
         "$BASE_DST\31.전사\인사팀" `
         "31 / 인사팀"

Copy-Dam "$BASE_SRC\33.우리동네TV\이미지 슬라이스" `
         "$BASE_DST\33.우리동네TV\이미지 슬라이스" `
         "33 / 이미지 슬라이스"

# ================================================================
# 섹션 3: 11.NEXT_UI — Tier 1 (작은 독립 서브 6개, 구조 다양성)
# ================================================================
Write-Host "`n### 섹션 3: 11.NEXT_UI Tier 1 (6개) ###" -ForegroundColor Cyan
$NUI = "$BASE_SRC\11.NEXT_UI_2022_10월오픈"
$NUI_DST = "$BASE_DST\11.NEXT_UI_2022_10월오픈"

Copy-Dam "$NUI\@AI P.A.N 특별관"              "$NUI_DST\@AI P.A.N 특별관"              "11/T1 @AI P.A.N 특별관"
Copy-Dam "$NUI\@skylife"                       "$NUI_DST\@skylife"                       "11/T1 @skylife"
Copy-Dam "$NUI\00_가이드"                      "$NUI_DST\00_가이드"                      "11/T1 00_가이드"
Copy-Dam "$NUI\■시연용_8월_10월이후 업데이트 금지" "$NUI_DST\■시연용_8월_10월이후 업데이트 금지" "11/T1 ■시연용"
Copy-Dam "$NUI\00_NVOD채널"                    "$NUI_DST\00_NVOD채널"                    "11/T1 00_NVOD채널"
Copy-Dam "$NUI\@모든G"                         "$NUI_DST\@모든G"                         "11/T1 @모든G"

# ================================================================
# 섹션 4: 11.NEXT_UI — Tier 2 (대형 시리즈 × 2022 + 2025, 시간 다양성)
# ================================================================
Write-Host "`n### 섹션 4: 11.NEXT_UI Tier 2 (6개 연도폴더) ###" -ForegroundColor Cyan

Copy-Dam "$NUI\@디자인산출물_가로포스터+단편상세\2022" "$NUI_DST\@디자인산출물_가로포스터+단편상세\2022" "11/T2 가로포스터 2022"
Copy-Dam "$NUI\@디자인산출물_가로포스터+단편상세\2025" "$NUI_DST\@디자인산출물_가로포스터+단편상세\2025" "11/T2 가로포스터 2025"
Copy-Dam "$NUI\@디자인산출물_오픈VOD\2022"            "$NUI_DST\@디자인산출물_오픈VOD\2022"            "11/T2 오픈VOD 2022"
Copy-Dam "$NUI\@디자인산출물_오픈VOD\2025"            "$NUI_DST\@디자인산출물_오픈VOD\2025"            "11/T2 오픈VOD 2025"
Copy-Dam "$NUI\■론칭이후_2022_10월\2022"              "$NUI_DST\■론칭이후_2022_10월\2022"              "11/T2 론칭이후 2022"
Copy-Dam "$NUI\■론칭이후_2022_10월\2025"              "$NUI_DST\■론칭이후_2022_10월\2025"              "11/T2 론칭이후 2025"

# ================================================================
# 완료 요약
# ================================================================
Write-Host "`n=== 복사 완료: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan
"=== 복사 완료: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -Append $LOG_FILE

Write-Host "`n[검증] 복사된 파일 수 확인:" -ForegroundColor Yellow
$fileCount = (Get-ChildItem -Path $BASE_DST -Recurse -File | Measure-Object).Count
$totalGB   = [math]::Round(
    (Get-ChildItem -Path $BASE_DST -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1GB, 2
)
Write-Host "  파일 수: $($fileCount.ToString('N0'))" -ForegroundColor Green
Write-Host "  용량:   $totalGB GB (PSD 제외 기준 예상 ~31 GB)" -ForegroundColor Green
Write-Host "`n로그: $LOG_FILE"
Write-Host "다음: Phase 2 파이프라인(썸네일·CLIP·pgvector) 시작 준비"
