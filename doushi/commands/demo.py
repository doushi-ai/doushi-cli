"""Demo command providing sample datasets for instant onboarding."""

import tempfile
from pathlib import Path
from typing import Optional
import typer
from rich.prompt import Prompt

from doushi.commands.train import train
from doushi.ui import console, print_banner, print_info

demo_app = typer.Typer(help="Spin up instant demo models with bundled datasets.")

SAMPLE_CHURN_CSV = """customer_id,credit_score,country,gender,age,tenure,balance,num_of_products,has_cr_card,is_active_member,estimated_salary,churn
15634602,619,France,Female,42,2,0.0,1,1,1,101348.88,1
15647311,608,Spain,Female,41,1,83807.86,1,0,1,112542.58,0
15619304,502,France,Female,42,8,159660.8,3,1,0,113931.57,1
15701354,699,France,Female,39,1,0.0,2,0,0,93826.63,0
15737888,850,Spain,Female,43,2,125510.82,1,1,1,79084.1,0
15574012,645,Spain,Male,44,8,113755.78,2,1,0,149756.71,1
15592531,822,France,Male,50,7,0.0,2,1,1,10062.8,0
15656148,376,Germany,Female,29,4,115046.74,4,1,0,119346.88,1
15792365,501,France,Male,44,4,142051.07,2,0,1,74940.5,0
15592389,684,France,Male,27,2,134603.88,1,1,1,71725.73,0
15767821,528,France,Male,31,6,102016.72,2,0,0,80181.12,0
15737173,497,Spain,Male,24,3,0.0,2,1,0,76390.01,0
15632264,476,France,Female,34,10,0.0,2,1,0,26260.98,0
15691483,549,France,Female,25,5,0.0,0,0,0,190857.79,0
15600882,635,Spain,Female,35,7,0.0,2,1,1,65951.65,0
15643966,616,Germany,Male,45,3,143129.41,2,0,1,6432.82,0
15738191,653,Germany,Male,58,1,132602.88,1,1,0,5097.67,1
15788295,549,Spain,Female,24,9,0.0,2,1,1,14408.85,0
15661507,587,Spain,Male,45,6,0.0,1,0,0,158684.81,0
15594720,678,France,Female,60,10,0.0,2,0,1,180749.43,0
15577657,732,France,Male,41,8,0.0,2,1,1,170886.17,0
15597945,636,Spain,Female,32,8,0.0,2,1,0,138555.46,0
15699309,510,Spain,Female,38,4,0.0,1,1,0,118913.53,1
15579769,669,France,Male,46,3,0.0,2,0,1,8487.75,0
15625047,846,France,Female,38,5,0.0,1,1,1,187616.16,0
15738198,577,France,Female,25,3,0.0,2,0,1,124508.29,0
15736816,756,Germany,Male,36,2,136815.6,1,1,0,170041.95,0
15700772,570,France,Female,44,9,0.0,1,1,1,40410.42,0
15728693,574,Germany,Female,43,3,141349.43,1,0,1,100187.43,0
15733883,411,France,Male,29,0,59697.17,2,1,1,53483.21,0
"""


@demo_app.command(name="demo")
def run_demo(
    save_local: bool = typer.Option(
        False,
        "--save-local",
        help="Save demo CSV to current working directory as 'sample_customer_churn.csv'",
    ),
) -> None:
    """Run an instant autonomous ML training demo using a sample customer churn dataset."""
    print_banner()
    console.print("\n[bold white]🚀 Doushi Instant 30-Second Demo[/bold white]\n")
    print_info("Creating temporary sample dataset: Customer Churn (30 records, 12 features)...")

    if save_local:
        demo_file = Path("./sample_customer_churn.csv")
    else:
        temp_dir = tempfile.mkdtemp()
        demo_file = Path(temp_dir) / "sample_customer_churn.csv"

    with open(demo_file, "w", encoding="utf-8") as f:
        f.write(SAMPLE_CHURN_CSV.strip())

    console.print(f"[dim]Dataset written to {demo_file}[/dim]\n")

    # Delegate to train command
    train(
        dataset_file=demo_file,
        goal="Predict if a banking customer will churn based on credit score, age, and balance",
        name="Demo Customer Churn Predictor",
        follow=True,
        json_output=False,
    )
