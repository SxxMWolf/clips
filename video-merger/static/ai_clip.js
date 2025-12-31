// AI 클립 생성 페이지 JavaScript

let currentVideoId = null;

// YouTube 영상 다운로드
const importYoutubeBtn = document.getElementById('import-youtube-btn');
if (importYoutubeBtn) {
    importYoutubeBtn.addEventListener('click', async () => {
    const url = document.getElementById('youtube-url').value;
    const prompt = document.getElementById('ai-prompt').value;
    
    if (!url) {
        showToast('YouTube URL을 입력하세요', 'error');
        return;
    }
    
    const btn = document.getElementById('import-youtube-btn');
    btn.disabled = true;
    btn.textContent = '다운로드 중...';
    
    try {
        const response = await fetch('/api/ai/import-youtube', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, prompt })
        });
        const result = await response.json();
        
        if (result.success) {
            currentVideoId = result.video_id;
            showToast(result.message, 'success');
            document.getElementById('video-status').style.display = 'block';
            checkVideoStatus();
        } else {
            showToast(result.message || '다운로드 실패', 'error');
        }
    } catch (error) {
        showToast('오류 발생: ' + error.message, 'error');
    }
    
    btn.disabled = false;
    btn.textContent = 'YouTube 영상 다운로드';
    });
}

// 비디오 상태 확인
async function checkVideoStatus() {
    if (!currentVideoId) return;
    
    try {
        const response = await fetch(`/api/ai/video-status/${currentVideoId}`);
        const status = await response.json();
        
        const statusInfo = document.getElementById('video-status-info');
        statusInfo.innerHTML = `
            <div><strong>비디오 ID:</strong> ${currentVideoId}</div>
            <div><strong>다운로드:</strong> ${status.downloaded ? '완료' : '진행 중'}</div>
            <div><strong>오디오 추출:</strong> ${status.audio_extracted ? '완료' : '진행 중'}</div>
            <div><strong>전사 완료:</strong> ${status.transcribed ? '완료' : '진행 중'}</div>
            ${status.duration ? `<div><strong>길이:</strong> ${Math.round(status.duration)}초</div>` : ''}
        `;
        
        if (status.transcribed) {
            document.getElementById('generate-clips-btn').style.display = 'block';
        }
    } catch (error) {
        console.error('상태 확인 오류:', error);
    }
}

// 클립 생성
const generateClipsBtn = document.getElementById('generate-clips-btn');
if (generateClipsBtn) {
    generateClipsBtn.addEventListener('click', async () => {
    if (!currentVideoId) return;
    
    const prompt = document.getElementById('ai-prompt').value;
    const btn = document.getElementById('generate-clips-btn');
    btn.disabled = true;
    btn.textContent = '클립 생성 중...';
    
    try {
        const response = await fetch('/api/ai/generate-clips', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_id: currentVideoId, prompt })
        });
        const result = await response.json();
        
        if (result.success) {
            showToast(result.message, 'success');
            setTimeout(loadClips, 3000);
        } else {
            showToast(result.message || '클립 생성 실패', 'error');
        }
    } catch (error) {
        showToast('오류 발생: ' + error.message, 'error');
    }
    
    btn.disabled = false;
    btn.textContent = 'AI 클립 생성';
    });
}

// 클립 목록 로드
async function loadClips() {
    if (!currentVideoId) return;
    
    try {
        const response = await fetch(`/api/ai/clips/${currentVideoId}`);
        const result = await response.json();
        
        if (result && result.clips && result.clips.length > 0) {
            document.getElementById('clips-section').style.display = 'block';
            const clipsList = document.getElementById('clips-list');
            
            clipsList.innerHTML = result.clips.map((clip, index) => `
                <div class="clip-card">
                    <h4>클립 ${index + 1}</h4>
                    <div class="clip-info">
                        <div><strong>훅:</strong> ${clip.hook}</div>
                        <div><strong>신뢰도:</strong> ${(clip.confidence * 100).toFixed(0)}%</div>
                        <div><strong>길이:</strong> ${clip.duration}초</div>
                        <div><strong>제목:</strong> ${clip.title || 'N/A'}</div>
                    </div>
                    ${clip.file_exists ? `
                        <video controls style="width: 100%; max-height: 300px; border-radius: 8px; margin: 10px 0;">
                            <source src="/api/ai/clip/file/${currentVideoId}/${clip.filename}" type="video/mp4">
                        </video>
                    ` : '<div style="color: #999;">처리 중...</div>'}
                </div>
            `).join('');
        } else {
            setTimeout(loadClips, 5000);
        }
    } catch (error) {
        console.error('클립 로드 오류:', error);
    }
}

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    // 상태 확인 주기적 실행 (비디오 ID가 있을 때만)
    if (currentVideoId) {
        setInterval(checkVideoStatus, 5000);
    }
});

