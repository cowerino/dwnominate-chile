"""
convergence_analysis.py - Análisis de convergencia para DW-NOMINATE C++

Genera gráficos de convergencia a partir de ejecuciones incrementales del
algoritmo. Soporta dos modos de entrada:

  Modo 1 (multi-run): Lee directorios iter_001/, iter_002/, ..., iter_N/
      generados por run_convergence.ps1. Calcula ‖Δx‖₂ real entre iteraciones.

  Modo 2 (log-only): Parsea un archivo .log de una ejecución con --verbose
      para extraer LL, W2, Beta, Clasificación. No puede calcular ‖Δx‖₂.

Uso:
    python tools/convergence_analysis.py --input-dir convergence_runs
    python tools/convergence_analysis.py --log-file model1_30iter.log
    python tools/convergence_analysis.py --input-dir convergence_runs --output-dir plots

Dependencias:
    pip install pandas matplotlib numpy
"""

import pandas as pd
import numpy as np
import matplotlib.ticker as mticker
import matplotlib.pyplot as plt
import argparse
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend no interactivo para generar archivos


# ============================================================
#  MODO 1: Lectura de ejecuciones multi-run
# ============================================================

def load_multirun_data(input_dir: Path) -> pd.DataFrame:
    """Carga datos de múltiples ejecuciones incrementales.

    Espera subdirectorios iter_001/, iter_002/, ..., iter_N/ cada uno
    conteniendo cpp_summary.csv y cpp_coordinates_all_periods.csv.

    Returns:
        DataFrame con columnas: iteration, log_likelihood, classification_pct,
        w2, beta, coord_change_l2, coord_change_max, coord_change_mean
    """
    iter_dirs = sorted(input_dir.glob("iter_*"))
    if not iter_dirs:
        raise FileNotFoundError(
            f"No se encontraron directorios iter_* en {input_dir}"
        )

    records = []
    prev_coords = None

    for iter_dir in iter_dirs:
        # Extraer número de iteración del nombre del directorio
        match = re.search(r"iter_(\d+)", iter_dir.name)
        if not match:
            continue
        iteration = int(match.group(1))

        summary_file = iter_dir / "cpp_summary.csv"
        coords_file = iter_dir / "cpp_coordinates_all_periods.csv"

        if not summary_file.exists():
            print(
                f"  WARN: {summary_file} no encontrado, saltando iter {iteration}")
            continue

        # Leer summary
        summary = pd.read_csv(summary_file)
        summary_dict = dict(zip(summary["parameter"], summary["value"]))

        record = {
            "iteration": iteration,
            "log_likelihood": float(summary_dict.get("log_likelihood", np.nan)),
            "classification_pct": float(summary_dict.get("classification_pct", np.nan)),
            "valid_votes": int(float(summary_dict.get("valid_votes", 0))),
            "correct_classifications": int(float(summary_dict.get("correct_classifications", 0))),
            "w2": float(summary_dict.get("w2", np.nan)),
            "beta": float(summary_dict.get("beta", np.nan)),
            "coord_change_l2": np.nan,
            "coord_change_max": np.nan,
            "coord_change_mean": np.nan,
            "bill_change_l2": np.nan,
        }

        # Leer coordenadas para calcular cambios
        if coords_file.exists():
            coords_df = pd.read_csv(coords_file)
            # Crear clave única (legislator_id, period)
            coords_df = coords_df.sort_values(
                ["legislator_id", "period"]).reset_index(drop=True)
            current_coords = coords_df[["coord1D", "coord2D"]].values

            if prev_coords is not None and current_coords.shape == prev_coords.shape:
                diff = current_coords - prev_coords
                record["coord_change_l2"] = np.linalg.norm(diff)
                record["coord_change_max"] = np.max(np.abs(diff))
                record["coord_change_mean"] = np.mean(np.abs(diff))

            prev_coords = current_coords.copy()

        # Leer bill parameters para calcular cambios
        bill_file = iter_dir / "cpp_bill_parameters.csv"
        if bill_file.exists():
            bills_df = pd.read_csv(bill_file)
            current_bills = bills_df[[
                "midpoint1D", "midpoint2D", "spread1D", "spread2D"]].values

            if hasattr(load_multirun_data, "_prev_bills"):
                prev_bills = load_multirun_data._prev_bills
                if current_bills.shape == prev_bills.shape:
                    bdiff = current_bills - prev_bills
                    record["bill_change_l2"] = np.linalg.norm(bdiff)

            load_multirun_data._prev_bills = current_bills.copy()

        records.append(record)

    return pd.DataFrame(records)


# ============================================================
#  MODO 2: Parseo de archivo log verbose
# ============================================================

def load_log_data(log_path: Path) -> pd.DataFrame:
    """Parsea un archivo .log de ejecución con --verbose.

    Extrae por iteración: W2, Beta, LL (post-SIGMAS), Clasificación.
    NO puede calcular ‖Δx‖₂ (no hay snapshots de coordenadas).

    Returns:
        DataFrame con columnas: iteration, log_likelihood,
        classification_pct, w2, beta
    """
    # Intentar varias codificaciones
    text = None
    for encoding in ["utf-16-le", "utf-16", "utf-8", "latin-1"]:
        try:
            text = log_path.read_text(encoding=encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if text is None:
        raise ValueError(f"No se pudo decodificar {log_path}")

    lines = text.splitlines()

    records = []
    current_iter = None
    current_record = {}

    # Patrones regex
    re_iter = re.compile(r"=== Iteracion global (\d+) ===")
    re_wint = re.compile(
        r"\[WINT\] W2:\s*([\d.]+)\s*->\s*([\d.]+),\s*LL:\s*([-\d.]+)"
    )
    re_sigmas = re.compile(
        r"\[SIGMAS\] Beta:\s*([\d.]+)\s*->\s*([\d.]+),\s*LL:\s*([-\d.]+)"
    )
    re_class = re.compile(
        r"Clasificacion:\s*(\d+)/(\d+)\s*\(([\d.]+)%\)"
    )
    re_timing = re.compile(
        r"\[TIMING iter (\d+)\]"
    )
    # Resultado final
    re_final_ll = re.compile(r"Log-likelihood:\s*([-\d.]+)")

    for line in lines:
        line = line.strip()

        m = re_iter.match(line)
        if m:
            # Guardar iteración anterior si existe
            if current_iter is not None and current_record:
                current_record["iteration"] = current_iter
                records.append(current_record)

            current_iter = int(m.group(1))
            current_record = {}
            continue

        m = re_wint.search(line)
        if m:
            current_record["w2_before"] = float(m.group(1))
            current_record["w2"] = float(m.group(2))
            current_record["ll_post_wint"] = float(m.group(3))
            continue

        m = re_sigmas.search(line)
        if m:
            current_record["beta_before"] = float(m.group(1))
            current_record["beta"] = float(m.group(2))
            current_record["ll_post_sigmas"] = float(m.group(3))
            continue

        m = re_class.search(line)
        if m:
            current_record["correct_classifications"] = int(m.group(1))
            current_record["valid_votes"] = int(m.group(2))
            current_record["classification_pct"] = float(m.group(3))
            continue

        m = re_timing.search(line)
        if m:
            # TIMING marca el fin de una iteración
            pass

    # Guardar última iteración
    if current_iter is not None and current_record:
        current_record["iteration"] = current_iter
        records.append(current_record)

    if not records:
        raise ValueError(
            f"No se encontraron datos de iteraciones en {log_path}")

    df = pd.DataFrame(records)

    # Usar LL post-SIGMAS como log_likelihood principal
    if "ll_post_sigmas" in df.columns:
        df["log_likelihood"] = df["ll_post_sigmas"]
    elif "ll_post_wint" in df.columns:
        df["log_likelihood"] = df["ll_post_wint"]

    # Calcular cambios en W2 y Beta entre iteraciones
    if "w2" in df.columns:
        df["delta_w2"] = df["w2"].diff().abs()
    if "beta" in df.columns:
        df["delta_beta"] = df["beta"].diff().abs()

    return df


# ============================================================
#  GENERACIÓN DE GRÁFICOS
# ============================================================

COLORS = {
    "ll": "#2563EB",         # azul
    "coord_l2": "#DC2626",   # rojo
    "coord_max": "#F59E0B",  # amarillo
    "class": "#059669",      # verde
    "w2": "#7C3AED",         # púrpura
    "beta": "#EA580C",       # naranja
    "bill_l2": "#6366F1",    # índigo
}


def plot_convergence_main(df: pd.DataFrame, output_path: Path, title_suffix: str = ""):
    """Gráfico principal: ‖Δx‖₂ vs LL por iteración (dual axis)."""
    has_coords = "coord_change_l2" in df.columns and df["coord_change_l2"].notna(
    ).any()

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Eje izquierdo: ‖Δx‖₂
    if has_coords:
        mask = df["coord_change_l2"].notna()
        ax1.plot(
            df.loc[mask, "iteration"],
            df.loc[mask, "coord_change_l2"],
            "o-",
            color=COLORS["coord_l2"],
            linewidth=2,
            markersize=6,
            label="‖Δx‖₂ (coordenadas)",
        )
        ax1.set_ylabel("‖Δx‖₂  (cambio en coordenadas)",
                       color=COLORS["coord_l2"], fontsize=12)
        ax1.tick_params(axis="y", labelcolor=COLORS["coord_l2"])

        # Línea de referencia para umbral de convergencia
        if df.loc[mask, "coord_change_l2"].max() > 1.0:
            ax1.axhline(
                y=1.0, color=COLORS["coord_l2"], linestyle=":", alpha=0.4, label="Umbral ‖Δx‖₂ = 1.0")
    else:
        # Si no hay datos de coordenadas, mostrar ΔW2 y ΔBeta
        if "delta_w2" in df.columns:
            ax1.plot(
                df["iteration"], df.get("delta_w2", []),
                "s-", color=COLORS["w2"], linewidth=1.5, markersize=5,
                label="ΔW₂"
            )
        if "delta_beta" in df.columns:
            ax1.plot(
                df["iteration"], df.get("delta_beta", []),
                "^-", color=COLORS["beta"], linewidth=1.5, markersize=5,
                label="ΔBeta"
            )
        ax1.set_ylabel("Cambio en parámetros globales", fontsize=12)

    ax1.set_xlabel("Iteración", fontsize=12)
    ax1.grid(True, alpha=0.3)

    # Eje derecho: Log-Likelihood
    ax2 = ax1.twinx()
    ax2.plot(
        df["iteration"],
        df["log_likelihood"],
        "D-",
        color=COLORS["ll"],
        linewidth=2,
        markersize=5,
        alpha=0.8,
        label="Log-Likelihood",
    )
    ax2.set_ylabel("Log-Likelihood", color=COLORS["ll"], fontsize=12)
    ax2.tick_params(axis="y", labelcolor=COLORS["ll"])

    # Media móvil de LL (ventana 5)
    if len(df) >= 5:
        ll_ma = df["log_likelihood"].rolling(window=5, min_periods=1).mean()
        ax2.plot(
            df["iteration"],
            ll_ma,
            "--",
            color=COLORS["ll"],
            alpha=0.4,
            linewidth=1.5,
            label="LL media móvil (5)",
        )

    # Leyendas combinadas
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc="upper right", fontsize=9)

    title = "Convergencia DW-NOMINATE: ‖Δx‖₂ y Log-Likelihood"
    if title_suffix:
        title += f" ({title_suffix})"
    plt.title(title, fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Gráfico guardado: {output_path}")


def plot_classification(df: pd.DataFrame, output_path: Path, title_suffix: str = ""):
    """Gráfico de estabilidad: % clasificación correcta vs iteración."""
    if "classification_pct" not in df.columns:
        print("  WARN: No hay datos de clasificación, saltando gráfico")
        return

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(
        df["iteration"],
        df["classification_pct"],
        "o-",
        color=COLORS["class"],
        linewidth=2,
        markersize=6,
        label="% Clasificación correcta",
    )

    # Media móvil
    if len(df) >= 5:
        class_ma = df["classification_pct"].rolling(
            window=5, min_periods=1).mean()
        ax.plot(
            df["iteration"],
            class_ma,
            "--",
            color=COLORS["class"],
            alpha=0.4,
            linewidth=1.5,
            label="Media móvil (5)",
        )

    # Banda de estabilidad (±0.1% de la media de las últimas 5)
    if len(df) >= 5:
        last_mean = df["classification_pct"].iloc[-5:].mean()
        ax.axhspan(last_mean - 0.1, last_mean + 0.1,
                   alpha=0.1, color=COLORS["class"])
        ax.axhline(y=last_mean, color=COLORS["class"], linestyle=":", alpha=0.5,
                   label=f"Media últimas 5: {last_mean:.2f}%")

    ax.set_xlabel("Iteración", fontsize=12)
    ax.set_ylabel("% Clasificación correcta", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    # Ajustar eje Y para dar contexto
    ymin = df["classification_pct"].min()
    ymax = df["classification_pct"].max()
    margin = max(0.5, (ymax - ymin) * 0.3)
    ax.set_ylim(ymin - margin, min(100.0, ymax + margin))

    title = "Estabilidad del Modelo: Clasificación Correcta"
    if title_suffix:
        title += f" ({title_suffix})"
    plt.title(title, fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Gráfico guardado: {output_path}")


def plot_parameters(df: pd.DataFrame, output_path: Path, title_suffix: str = ""):
    """Gráfico auxiliar: evolución de W2 y Beta."""
    has_w2 = "w2" in df.columns and df["w2"].notna().any()
    has_beta = "beta" in df.columns and df["beta"].notna().any()

    if not has_w2 and not has_beta:
        return

    fig, ax1 = plt.subplots(figsize=(12, 5))

    if has_w2:
        ax1.plot(
            df["iteration"], df["w2"],
            "s-", color=COLORS["w2"], linewidth=2, markersize=5,
            label="W₂"
        )
    ax1.set_xlabel("Iteración", fontsize=12)
    ax1.set_ylabel("W₂", color=COLORS["w2"], fontsize=12)
    ax1.tick_params(axis="y", labelcolor=COLORS["w2"])
    ax1.grid(True, alpha=0.3)

    if has_beta:
        ax2 = ax1.twinx()
        ax2.plot(
            df["iteration"], df["beta"],
            "^-", color=COLORS["beta"], linewidth=2, markersize=5,
            label="Beta (β)"
        )
        ax2.set_ylabel("Beta (β)", color=COLORS["beta"], fontsize=12)
        ax2.tick_params(axis="y", labelcolor=COLORS["beta"])

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=10)
    else:
        ax1.legend(fontsize=10)

    title = "Evolución de Parámetros Globales"
    if title_suffix:
        title += f" ({title_suffix})"
    plt.title(title, fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Gráfico guardado: {output_path}")


def plot_coord_detail(df: pd.DataFrame, output_path: Path, title_suffix: str = ""):
    """Gráfico detallado de cambios en coordenadas: L2, max, mean."""
    metrics = ["coord_change_l2", "coord_change_max", "coord_change_mean"]
    available = [m for m in metrics if m in df.columns and df[m].notna().any()]

    if not available:
        return

    fig, ax = plt.subplots(figsize=(12, 5))

    labels_map = {
        "coord_change_l2": ("‖Δx‖₂ (norma L2)", COLORS["coord_l2"], "o-"),
        "coord_change_max": ("Δx_max (cambio máximo)", COLORS["coord_max"], "s-"),
        "coord_change_mean": ("Δx_mean (cambio medio)", COLORS["class"], "^-"),
    }

    for metric in available:
        label, color, style = labels_map[metric]
        mask = df[metric].notna()
        ax.plot(
            df.loc[mask, "iteration"], df.loc[mask, metric],
            style, color=color, linewidth=2, markersize=5, label=label
        )

    ax.set_xlabel("Iteración", fontsize=12)
    ax.set_ylabel("Cambio en coordenadas", fontsize=12)
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend(fontsize=10)

    title = "Detalle de Cambios en Coordenadas de Legisladores"
    if title_suffix:
        title += f" ({title_suffix})"
    plt.title(title, fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Gráfico guardado: {output_path}")


def print_convergence_summary(df: pd.DataFrame):
    """Imprime un resumen de convergencia en consola."""
    print("\n" + "=" * 60)
    print("  RESUMEN DE CONVERGENCIA")
    print("=" * 60)

    n = len(df)
    print(f"  Iteraciones analizadas: {n}")

    if "log_likelihood" in df.columns:
        ll_first = df["log_likelihood"].iloc[0]
        ll_last = df["log_likelihood"].iloc[-1]
        ll_best = df["log_likelihood"].max()
        print(f"  Log-Likelihood:")
        print(f"    Primera iteración: {ll_first:.2f}")
        print(f"    Última iteración:  {ll_last:.2f}")
        print(f"    Mejor valor:       {ll_best:.2f}")
        print(f"    Mejora total:      {ll_last - ll_first:+.2f}")

    if "classification_pct" in df.columns and df["classification_pct"].notna().any():
        cl_first = df["classification_pct"].iloc[0]
        cl_last = df["classification_pct"].iloc[-1]
        print(f"  Clasificación:")
        print(f"    Primera iteración: {cl_first:.2f}%")
        print(f"    Última iteración:  {cl_last:.2f}%")

    if "w2" in df.columns:
        print(f"  W₂: {df['w2'].iloc[0]:.4f} → {df['w2'].iloc[-1]:.4f}")
    if "beta" in df.columns:
        print(f"  Beta: {df['beta'].iloc[0]:.4f} → {df['beta'].iloc[-1]:.4f}")

    has_coords = "coord_change_l2" in df.columns and df["coord_change_l2"].notna(
    ).any()
    if has_coords:
        mask = df["coord_change_l2"].notna()
        coords = df.loc[mask, "coord_change_l2"]
        print(f"  ‖Δx‖₂ (cambio coordenadas):")
        print(f"    Primera: {coords.iloc[0]:.4f}")
        print(f"    Última:  {coords.iloc[-1]:.4f}")
        print(f"    Mínima:  {coords.min():.4f}")

        # Detectar convergencia
        if len(coords) >= 3:
            last3 = coords.iloc[-3:]
            mean_l2 = coords.iloc[-1]
            num_legs = 760  # estimación basada en output
            mean_per_leg = mean_l2 / num_legs if num_legs > 0 else mean_l2

            if mean_per_leg < 0.005:
                print(
                    f"    → CONVERGIDO (cambio medio/legislador = {mean_per_leg:.6f} < 0.005)")
            elif mean_per_leg < 0.02:
                print(
                    f"    → CASI CONVERGIDO (cambio medio/legislador = {mean_per_leg:.6f})")
            else:
                print(
                    f"    → AÚN NO CONVERGE (cambio medio/legislador = {mean_per_leg:.6f})")

    # Diagnóstico de oscilaciones en LL
    if "log_likelihood" in df.columns and n >= 6:
        ll = df["log_likelihood"].values
        # Calcular amplitud de oscilación en las últimas iteraciones
        tail = ll[max(0, n-5):]
        amplitude = tail.max() - tail.min()
        mean_ll = np.mean(tail)
        rel_amplitude = amplitude / abs(mean_ll) if mean_ll != 0 else 0

        print(f"  Oscilación LL (últimas 5):")
        print(f"    Amplitud: {amplitude:.2f}")
        print(f"    Relativa: {rel_amplitude:.6f}")

        if rel_amplitude < 0.001:
            print(f"    → LL estable (oscilación < 0.1%)")
        elif rel_amplitude < 0.01:
            print(
                f"    → Ciclo límite normal (oscilación {rel_amplitude*100:.2f}%)")
        else:
            print(f"    → Oscilación significativa ({rel_amplitude*100:.2f}%)")

    print("=" * 60 + "\n")


def export_metrics_csv(df: pd.DataFrame, output_path: Path):
    """Exporta métricas de convergencia a CSV."""
    cols = [c for c in [
        "iteration", "log_likelihood", "classification_pct",
        "w2", "beta", "coord_change_l2", "coord_change_max",
        "coord_change_mean", "bill_change_l2",
    ] if c in df.columns]

    df[cols].to_csv(output_path, index=False, float_format="%.6f")
    print(f"  Métricas exportadas: {output_path}")


# ============================================================
#  MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Análisis de convergencia para DW-NOMINATE C++",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python tools/convergence_analysis.py --input-dir convergence_runs
  python tools/convergence_analysis.py --log-file model1_30iter.log
  python tools/convergence_analysis.py --input-dir convergence_runs --output-dir plots --title "Modelo 1"
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--input-dir",
        type=Path,
        help="Directorio con subdirectorios iter_001/, iter_002/, ... (modo multi-run)",
    )
    group.add_argument(
        "--log-file",
        type=Path,
        help="Archivo .log de ejecución verbose (modo log-only)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directorio donde guardar gráficos (default: junto a input)",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="",
        help="Sufijo para títulos de gráficos (ej: 'Modelo 1')",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="png",
        choices=["png", "pdf", "svg"],
        help="Formato de salida de gráficos (default: png)",
    )

    args = parser.parse_args()

    # Determinar modo y cargar datos
    if args.input_dir:
        input_dir = args.input_dir
        if not input_dir.exists():
            print(f"ERROR: Directorio no encontrado: {input_dir}")
            sys.exit(1)

        print(f"Modo: multi-run (leyendo de {input_dir}/)")
        df = load_multirun_data(input_dir)
        output_dir = args.output_dir or input_dir
        mode = "multirun"
    else:
        log_file = args.log_file
        if not log_file.exists():
            print(f"ERROR: Archivo no encontrado: {log_file}")
            sys.exit(1)

        print(f"Modo: log-only (parseando {log_file})")
        df = load_log_data(log_file)
        output_dir = args.output_dir or log_file.parent
        mode = "log"

    output_dir.mkdir(parents=True, exist_ok=True)
    fmt = args.format
    title = args.title

    print(f"  Iteraciones cargadas: {len(df)}")
    print(f"  Output: {output_dir}/")

    # Generar gráficos
    print("\nGenerando gráficos...")

    plot_convergence_main(
        df, output_dir / f"convergence_main.{fmt}", title
    )
    plot_classification(
        df, output_dir / f"convergence_classification.{fmt}", title
    )
    plot_parameters(
        df, output_dir / f"convergence_parameters.{fmt}", title
    )

    if mode == "multirun":
        plot_coord_detail(
            df, output_dir / f"convergence_coord_detail.{fmt}", title
        )

    # Exportar métricas
    export_metrics_csv(df, output_dir / "convergence_metrics.csv")

    # Resumen en consola
    print_convergence_summary(df)


if __name__ == "__main__":
    main()
