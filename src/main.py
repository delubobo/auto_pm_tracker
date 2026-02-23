import pandas as pd
import datetime
import plotly.express as px
import typer
import sqlite3
from src.database import initialize_db, seed_data, DB_PATH
from src.cpm import calculate_critical_path # NEW IMPORT
from src.services import calculate_project_evm

# Initialize the Typer application
app = typer.Typer(
    name="pm-tracker",
    help="An automated Project Management CLI for schedule analysis and AI reporting.",
    add_completion=False
)

@app.command()
def init(force: bool = typer.Option(False, "--force", help="Required to drop and recreate the tasks table.")):
    """Initialize the project database. Requires --force to prevent accidental data loss."""
    if not force:
        typer.secho(
            "ERROR: 'init' will DROP the tasks table and destroy all data.\n"
            "Re-run with --force if you are sure.",
            fg=typer.colors.RED,
            bold=True,
        )
        raise typer.Exit(code=1)
    typer.secho("Initializing project database...", fg=typer.colors.BLUE)
    initialize_db()
    seed_data()
    typer.secho("Project database initialized and seeded successfully.", fg=typer.colors.GREEN)


@app.command()
def seed_demo():
    """Seed the 18-task residential construction demo project ($280K BAC)."""
    from src.demo_data import seed_demo_data
    typer.secho("Seeding demo project data...", fg=typer.colors.BLUE)
    seed_demo_data()
    typer.secho("Demo project seeded. Run 'critical-path' and 'financials' to explore.", fg=typer.colors.GREEN)

@app.command()
def status():
    """Print the current health and status of the project schedule."""
    typer.secho("Fetching project status...", fg=typer.colors.BLUE)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, task_name, status, duration_days FROM tasks")
            tasks = cursor.fetchall()
            
            if not tasks:
                typer.secho("No tasks found. Run 'init' first.", fg=typer.colors.YELLOW)
                return
            
            typer.secho(f"{'ID':<5} | {'Task Name':<20} | {'Status':<15} | {'Duration'}", bold=True)
            typer.secho("-" * 55)
            for task in tasks:
                typer.echo(f"{task[0]:<5} | {task[1]:<20} | {task[2]:<15} | {task[3]} days")
                
    except sqlite3.Error as e:
        typer.secho(f"Database error: {e}", fg=typer.colors.RED)

# NEW COMMAND ADDED HERE
@app.command()
def critical_path():
    """Calculate the project Critical Path Method (CPM) and identify bottlenecks."""
    typer.secho("Analyzing schedule network diagram...", fg=typer.colors.BLUE)
    results = calculate_critical_path()
    
    if not results:
        typer.secho("No schedule data found.", fg=typer.colors.YELLOW)
        return

    typer.secho(f"{'Task Name':<20} | {'ES':<3} | {'EF':<3} | {'LS':<3} | {'LF':<3} | {'Float':<5} | {'Critical?'}", bold=True)
    typer.secho("-" * 65)
    
    for r in results:
        # Highlight critical path items in red
        is_crit = "YES" if r['is_critical'] else "NO"
        color = typer.colors.RED if r['is_critical'] else typer.colors.WHITE
        
        row_text = f"{r['name']:<20} | {r['es']:<3} | {r['ef']:<3} | {r['ls']:<3} | {r['lf']:<3} | {r['float']:<5} | {is_crit}"
        typer.secho(row_text, fg=color)
@app.command()
def financials():
    """Calculate Earned Value Management (EVM) metrics for the project."""
    typer.secho("Calculating project financial health...", fg=typer.colors.BLUE)
    metrics = calculate_project_evm()
    
    if not metrics:
        typer.secho("No project data available for calculation.", fg=typer.colors.YELLOW)
        return

    # Determine health colors
    cpi_color = typer.colors.GREEN if metrics["CPI"] >= 1.0 else typer.colors.RED
    spi_color = typer.colors.GREEN if metrics["SPI"] >= 1.0 else typer.colors.RED

    typer.secho("\n--- EXECUTIVE FINANCIAL SUMMARY ---", bold=True)
    typer.echo(f"Budget at Completion (BAC): ${metrics['BAC']:,.2f}")
    typer.echo(f"Planned Value (PV):       ${metrics['PV']:,.2f}")
    typer.echo(f"Earned Value (EV):        ${metrics['EV']:,.2f}")
    typer.echo(f"Actual Cost (AC):         ${metrics['AC']:,.2f}\n")
    
    typer.secho("--- PERFORMANCE INDICES ---", bold=True)
    typer.secho(f"Cost Performance Index (CPI):    {metrics['CPI']}", fg=cpi_color)
    typer.secho(f"Schedule Performance Index (SPI): {metrics['SPI']}", fg=spi_color)
    
    typer.echo(f"\nEstimate at Completion (EAC): ${metrics['EAC']:,.2f}")
    
    # Provide an automated insight
    if metrics["CPI"] < 1.0:
        typer.secho("WARNING: Project is currently over budget.", fg=typer.colors.RED, bold=True)
    if metrics["SPI"] < 1.0:
        typer.secho("WARNING: Project is currently behind schedule.", fg=typer.colors.RED, bold=True)
@app.command()
def export():
    """Export the current project schedule and financial data to a CSV file."""
    typer.secho("Extracting database records...", fg=typer.colors.BLUE)
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Pandas can read SQL queries directly and convert them to a DataFrame
            df = pd.read_sql_query("SELECT * FROM tasks", conn)
            
        if df.empty:
            typer.secho("Database is empty. Nothing to export.", fg=typer.colors.YELLOW)
            return
            
        export_path = "data/project_export.csv"
        df.to_csv(export_path, index=False)
        typer.secho(f"Success! Project data exported to {export_path}", fg=typer.colors.GREEN)
        
    except Exception as e:
        typer.secho(f"Export failed: {e}", fg=typer.colors.RED)
@app.command()
def gantt():
    """Generate an interactive Gantt chart from the project schedule."""
    typer.secho("Generating Gantt chart...", fg=typer.colors.BLUE)
    
    # We use our Sprint 1 logic as the brain for our visualization
    from src.cpm import calculate_critical_path
    results = calculate_critical_path()
    
    if not results:
        typer.secho("No schedule data found.", fg=typer.colors.YELLOW)
        return
        
    # Convert relative project days into actual calendar dates
    project_start_date = datetime.date.today()
    chart_data = []
    
    for r in results:
        start_date = project_start_date + datetime.timedelta(days=r['es'])
        end_date = project_start_date + datetime.timedelta(days=r['ef'])
        
        # We handle tasks with zero duration by giving them a minimal visual width
        if start_date == end_date:
            end_date = start_date + datetime.timedelta(days=0.5)
            
        chart_data.append({
            "Task": r['name'],
            "Start": start_date,
            "Finish": end_date,
            "Critical": "Critical Path" if r['is_critical'] else "Non-Critical"
        })
        
    df = pd.DataFrame(chart_data)
    
    # Create the Plotly Gantt chart
    fig = px.timeline(
        df, 
        x_start="Start", 
        x_end="Finish", 
        y="Task", 
        color="Critical",
        color_discrete_map={"Critical Path": "red", "Non-Critical": "blue"},
        title="Project Schedule Gantt Chart"
    )
    
    # Reverse the Y-axis so the first task is at the top of the chart
    fig.update_yaxes(autorange="reversed")
    
    # Save to HTML and automatically open it in your browser
    export_path = "data/gantt_chart.html"
    fig.write_html(export_path)
    typer.secho(f"Success! Interactive Gantt chart saved to {export_path}", fg=typer.colors.GREEN)
    
    import webbrowser
    webbrowser.open(export_path)

if __name__ == "__main__":
    app()