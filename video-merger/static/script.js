// API 호출 함수
async function apiCall(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('API 호출 오류:', error);
        showToast('오류가 발생했습니다: ' + error.message, 'error');
        return { success: false, message: error.message };
    }
}

// 상태 업데이트
async function updateStatus() {
    try {
        const status = await apiCall('/api/status');
        
        // 원본 영상
        const rawCount = document.getElementById('raw-count');
        if (rawCount) {
            rawCount.textContent = status.raw_count || 0;
        }
        const rawList = document.getElementById('raw-list');
        if (rawList) {
            if (status.raw_videos && status.raw_videos.length > 0) {
                rawList.innerHTML = status.raw_videos.map(video => 
                    `<div>${video}</div>`
                ).join('');
            } else {
                rawList.innerHTML = '<div style="color: #999;">영상이 없습니다</div>';
            }
        }
        
        // 병합된 영상
        const mergedStatus = document.getElementById('merged-status');
        const mergedSize = document.getElementById('merged-size');
        const mergedPreview = document.getElementById('merged-preview');
        
        if (mergedStatus) {
            if (status.merged_exists) {
                mergedStatus.textContent = '준비됨';
                mergedStatus.style.color = '#28a745';
                if (mergedSize) mergedSize.textContent = `크기: ${status.merged_size} MB`;
                if (mergedPreview) {
                    mergedPreview.innerHTML = `
                        <video controls style="width: 100%; border-radius: 10px; max-height: 300px;">
                            <source src="/videos/short.mp4" type="video/mp4">
                        </video>
                    `;
                }
            } else {
                mergedStatus.textContent = '없음';
                mergedStatus.style.color = '#999';
                if (mergedSize) mergedSize.textContent = '';
                if (mergedPreview) mergedPreview.innerHTML = '';
            }
        }
        
    } catch (error) {
        console.error('상태 업데이트 오류:', error);
    }
}

// 토스트 알림 표시
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// 이벤트 리스너는 각 페이지의 전용 스크립트에서 처리됩니다
// - merge.html: 인라인 스크립트
// - upload.js: 업로드 페이지 전용


// 메타데이터 관련 기능은 현재 사용되지 않음 (제거됨)

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    // 상태 업데이트 (요소가 있는 경우에만)
    const rawCount = document.getElementById('raw-count');
    const mergedStatus = document.getElementById('merged-status');
    if (rawCount || mergedStatus) {
        updateStatus();
        setInterval(updateStatus, 5000);
    }
    
    // 메타데이터 로드 (요소가 있는 경우에만)
    const titleInput = document.getElementById('title');
    if (titleInput) {
        loadMetadata();
    }
});

