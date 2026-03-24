from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

def keep_alive():
    # 이곳을 실제 Streamlit 앱 주소로 변경하세요
    url = "https://y00nportfolio.streamlit.app/" 

    options = Options()
    options.add_argument('--headless') # 화면 없이 백그라운드에서 실행
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # 가상 브라우저 실행 및 접속
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        print(f"접속 시도: {url}")
        driver.get(url)
        time.sleep(10) # 앱이 완전히 로딩되고 웹소켓이 연결될 때까지 10초 대기
        print("접속 및 깨우기 성공!")
    except Exception as e:
        print(f"에러 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    keep_alive()
