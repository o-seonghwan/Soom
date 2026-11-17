"""강남 위험지도를 갱신한 뒤 저장된 최종 모델로 마포 외부 검증을 실행한다."""
import subprocess
import sys
from pathlib import Path


def main():
    code = Path(__file__).resolve().parents[1]
    scripts = (
        ("강남 XGBoost 깊이 3 학습 및 위험지도 갱신", code / "1_모델학습" / "1_B2C_비흡연자_간접흡연위험지도.py"),
        ("마포 외부 검증", code / "3_선택" / "1_마포_외부검증.py"),
    )
    for title, path in scripts:
        print(f"\n<{title}>", flush=True)
        subprocess.run([sys.executable, str(path)], cwd=path.parent, check=True)


if __name__ == "__main__":
    main()
