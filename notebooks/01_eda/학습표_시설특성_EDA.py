"""학습표의 상가·정류소·건물·시설 특성 분포를 한글 표와 그림으로 저장한다."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter


def configure_font(font_path):
    if font_path:
        font_manager.fontManager.addfont(font_path)
        family = font_manager.FontProperties(fname=font_path).get_name()
    else:
        available = {font.name for font in font_manager.fontManager.ttflist}
        family = next(
            (name for name in ("Malgun Gothic", "Noto Sans CJK KR", "Noto Sans KR",
                               "AppleGothic", "NanumGothic") if name in available),
            None,
        )
        if family is None:
            raise RuntimeError("한글 글꼴을 설치하거나 --font로 글꼴 파일을 지정하세요.")
    plt.rcParams.update({"font.family": family, "axes.unicode_minus": False})


def frequency(values, edges, labels):
    groups = pd.cut(values, edges, labels=labels, right=False)
    return groups.value_counts(sort=False)


def style_axis(ax, label, horizontal=False):
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x" if horizontal else "y", alpha=0.2)
    if horizontal:
        ax.set_xlabel(label)
    else:
        ax.set_ylabel(label)


def save_distribution(out, name, counts, title):
    fig, ax = plt.subplots(figsize=(8.6, 3.8), layout="constrained")
    bars = ax.barh(counts.index.astype(str), counts, color="#79a76b")
    ax.bar_label(bars, labels=[f"{n:,}" for n in counts], padding=5)
    ax.set_xlim(0, max(counts) * 1.18)
    ax.invert_yaxis()
    ax.set_title(title, loc="left", weight="bold")
    style_axis(ax, "보행 지점 수", horizontal=True)
    fig.savefig(out / f"{name}.png", dpi=210)
    plt.close(fig)
    counts.rename("보행 지점 수").rename_axis("구간").to_csv(
        out / f"{name}.csv", encoding="utf-8-sig"
    )


def plot_store_rates(data, out):
    counts = data["상가_50m"]
    last = int(counts.max()) // 10
    groups = pd.cut(counts, np.arange(last + 2) * 10, right=False)
    summary = data.groupby(groups, observed=False)["정답"].agg(
        전체지점="size", 양성지점="sum"
    )
    summary["양성비율"] = summary["양성지점"] / summary["전체지점"].replace(0, np.nan)
    summary.index = [f"{b.left}~{b.right - 1}개" for b in summary.index]
    summary.rename_axis("반경 50m 상가 수").to_csv(
        out / "상가_10개_간격_양성라벨.csv", encoding="utf-8-sig"
    )
    shown = summary.iloc[:10]
    tail = summary.iloc[10:]["전체지점"].sum()
    fig, (ax, count_ax) = plt.subplots(
        2, 1, figsize=(10.2, 5.8), sharex=True,
        gridspec_kw={"height_ratios": [2, 1]}, layout="constrained",
    )
    bars = ax.bar(shown.index, shown["양성비율"], color="#4f8a35")
    ax.bar_label(bars, labels=[f"{v:.1%}" if pd.notna(v) else "" for v in shown["양성비율"]], padding=4)
    ax.axhline(data["정답"].mean(), linestyle="--", color="#637269", label="전체 양성 라벨 비율")
    ax.set_ylim(0, max(shown["양성비율"].max(), data["정답"].mean()) * 1.25)
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(loc="upper left", frameon=False)
    ax.set_title("상가 수 10개 간격으로 본 양성 라벨 비율", loc="left", weight="bold")
    style_axis(ax, "양성 라벨 비율")
    bars = count_ax.bar(shown.index, shown["전체지점"], color="#a5c69a")
    count_ax.bar_label(bars, labels=[f"{n:,}" for n in shown["전체지점"]], padding=3, fontsize=8)
    count_ax.set_ylim(0, max(shown["전체지점"]) * 1.23)
    style_axis(count_ax, "전체 지점 수")
    count_ax.set_xlabel(
        f"반경 50m 상가 수 · {len(data):,}개 지점 중 100개 이상 {tail:,}개는 전체 구간 CSV에 수록"
    )
    fig.savefig(out / "상가_10개_간격_양성라벨.png", dpi=210)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training_csv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()
    configure_font(args.font)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cols = ["상가_50m", "정답", "정류소_거리m", "건물연면적_50m", "지하철출입구_거리m", "어린이집_거리m"]
    data = pd.read_csv(args.training_csv, usecols=cols)
    if data.empty or data[cols].isna().any().any() or not data["정답"].isin([0, 1]).all():
        raise ValueError("필요한 변수가 결측 없이 들어 있고 정답이 0 또는 1인 학습표가 필요합니다.")
    plot_store_rates(data, args.output_dir)
    distance_edges = [0, 50, 100, 200, 300, np.inf]
    distance_labels = ["50m 미만", "50~100m 미만", "100~200m 미만", "200~300m 미만", "300m 이상"]
    for col, name in (("정류소_거리m", "버스정류소"), ("지하철출입구_거리m", "지하철출입구"),
                      ("어린이집_거리m", "어린이집")):
        counts = frequency(data[col], distance_edges, distance_labels)
        save_distribution(args.output_dir, f"{name}_최근접거리", counts, f"{name}까지의 최근접 직선거리")
    area = data["건물연면적_50m"]
    positive = frequency(area[area > 0], [0, 10000, 25000, np.inf],
                         ["0㎡ 초과~1만㎡ 미만", "1만~2.5만㎡ 미만", "2.5만㎡ 이상"])
    counts = pd.concat([pd.Series({"0㎡": area.eq(0).sum()}), positive])
    save_distribution(args.output_dir, "건물_50m_연면적", counts, "반경 50m 내 건물 연면적 합계")


if __name__ == "__main__":
    main()
