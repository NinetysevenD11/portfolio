.glass-card {
        background: rgba(255, 255, 255, 0.7) !important; /* 텍스트 가독성을 위해 살짝 덜 투명하게 */
        backdrop-filter: blur(20px) saturate(150%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(150%) !important;
        
        /* 2) 구분이 명확한 진한 민트 테두리 */
        border: 1.5px solid rgba(16, 185, 129, 0.35) !important; 
        border-top: 1.5px solid rgba(16, 185, 129, 0.6) !important; /* 빛이 들어오는 위쪽을 더 진하게 잡아 형태감을 줍니다 */
        border-radius: 24px !important;
        padding: 24px !important;
        
        /* 1) 양각(Embossed) 느낌의 입체감 그림자 */
        box-shadow: 
            6px 8px 20px rgba(4, 120, 87, 0.08),       /* 우측 하단 짙은 녹색 그림자 (밖으로 튀어나온 느낌) */
            -4px -4px 12px rgba(255, 255, 255, 0.9),   /* 좌측 상단 밝은 그림자 (양각 효과 극대화) */
            inset 2px 2px 4px rgba(255, 255, 255, 1),  /* 카드 안쪽 좌측 상단의 하이라이트 */
            inset -2px -2px 6px rgba(16, 185, 129, 0.05) !important; /* 카드 안쪽 우측 하단의 얕은 음영 */
            
        height: 100%; 
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }

    .glass-card:hover {
        transform: translateY(-4px); /* 호버 시 조금 더 위로 떠오르게 */
        border: 1.5px solid rgba(16, 185, 129, 0.6) !important; /* 호버 시 테두리를 더 선명하게 */
        box-shadow: 
            8px 12px 24px rgba(4, 120, 87, 0.12),
            -6px -6px 16px rgba(255, 255, 255, 1),
            inset 2px 2px 4px rgba(255, 255, 255, 1),
            inset -2px -2px 6px rgba(16, 185, 129, 0.05) !important;
    }
