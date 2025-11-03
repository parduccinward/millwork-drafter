#!/usr/bin/env python3
"""
Millwork Drafter - Main CLI Entry Point

Parametric, CSV-driven pipeline for generating vector PDFs of millwork shop drawings.
Based on memory-banks specifications with Anti-Over-Engineering guardrails.
"""

import sys
import click
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config import ConfigLoader, MillworkConfig


@click.command()
@click.option(
    "--input", "-i",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to input CSV file containing room specifications"
)
@click.option(
    "--config", "-c", 
    type=click.Path(exists=True, path_type=Path),
    default="config/default.yaml",
    help="Path to YAML configuration file (default: config/default.yaml)"
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default="output/pdfs",
    help="Output directory for generated PDFs (default: output/pdfs)"
)
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings as errors and fail the batch"
)
@click.option(
    "--units",
    type=click.Choice(["in", "mm"], case_sensitive=False),
    default="in",
    help="Display units for dimensions (default: in)"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate inputs without generating PDFs"
)
@click.version_option(version="0.1.0", prog_name="Millwork Drafter")
def main(
    input: Path,
    config: Path,
    output: Path,
    strict: bool,
    units: str,
    verbose: bool,
    dry_run: bool
) -> None:
    """
    Generate millwork shop drawing PDFs from CSV specifications.
    
    This tool implements a parametric, CSV-driven pipeline that generates
    vector PDFs for millwork shop drawings following professional standards
    and ADA compliance requirements.
    
    Examples:
    
        # Generate PDFs with default configuration
        python generate.py --input input/rooms.csv
        
        # Use custom config and strict validation
        python generate.py -i input/rooms.csv -c config/project_alpha.yaml --strict
        
        # Dry run to validate inputs only
        python generate.py -i input/rooms.csv --dry-run --verbose
    """
    
    try:
        # Set up output directories
        output.mkdir(parents=True, exist_ok=True)
        (output.parent / "logs").mkdir(parents=True, exist_ok=True)
        
        if verbose:
            click.echo(f"Input CSV: {input}")
            click.echo(f"Configuration: {config}")
            click.echo(f"Output directory: {output}")
            click.echo(f"Units: {units}")
            click.echo(f"Strict mode: {strict}")
            click.echo(f"Dry run: {dry_run}")
        
        # Load configuration
        if verbose:
            click.echo("Loading configuration...")
        
        config_loader = ConfigLoader()
        try:
            config_dict = config_loader.load_config(str(config))
            config_hash = config_loader.get_config_hash(config_dict)
            
            if verbose:
                click.echo(f"Configuration loaded successfully (hash: {config_hash[:8]}...)")
        
        except Exception as e:
            click.echo(f"Error: Failed to load configuration: {e}", err=True)
            sys.exit(2)
        
        # Validate CSV file exists and is readable
        if not input.exists():
            click.echo(f"Error: Input file not found: {input}", err=True)
            sys.exit(2)
        
        if not input.suffix.lower() == '.csv':
            click.echo(f"Warning: Input file does not have .csv extension: {input}", err=True)
            if strict:
                sys.exit(1)
        
        if verbose:
            click.echo(f"Input CSV validated: {input}")
        
        # Parse and validate CSV data
        if verbose:
            click.echo("Parsing and validating CSV data...")
        
        try:
            from src.parser import CSVParser, RoomValidator, ErrorReporter
            
            # Initialize parser and validator
            csv_parser = CSVParser()
            validator = RoomValidator(strict_mode=strict)
            error_reporter = ErrorReporter(output)
            
            # Parse CSV file
            parsed_rooms, parse_result = csv_parser.parse_file(input)
            
            if not parse_result.is_valid:
                click.echo(f"Error: CSV parsing failed with {len(parse_result.errors)} errors:", err=True)
                for error in parse_result.errors[:5]:  # Show first 5 errors
                    click.echo(f"  {error.field}: {error.message}", err=True)
                if len(parse_result.errors) > 5:
                    click.echo(f"  ... and {len(parse_result.errors) - 5} more errors", err=True)
                sys.exit(1)
            
            if verbose:
                click.echo(f"Successfully parsed {len(parsed_rooms)} rooms from CSV")
            
            # Validate parsed data
            valid_rooms, batch_summary = validator.validate_batch(parsed_rooms, config_dict)
            
            # Write error reports
            for room_data in parsed_rooms:
                validation_result = validator.validate_room_data(room_data, config_dict)
                if not validation_result.is_valid or validation_result.warnings:
                    error_reporter.write_room_errors(room_data.room_id, validation_result)
            
            error_reporter.write_batch_summary(batch_summary, str(input), str(config))
            
            # Report validation results
            if verbose or batch_summary.failed_rows > 0:
                click.echo(f"Validation Summary:")
                click.echo(f"  Total rooms: {batch_summary.total_rows}")
                click.echo(f"  Valid rooms: {batch_summary.successful_rows}")
                click.echo(f"  Failed rooms: {batch_summary.failed_rows}")
                if batch_summary.failed_rows > 0:
                    click.echo(f"  Success rate: {batch_summary.successful_rows/batch_summary.total_rows*100:.1f}%")
            
            if batch_summary.failed_rows > 0:
                click.echo(f"Warning: {batch_summary.failed_rows} rooms failed validation. See logs in {output}/logs/", err=True)
                if strict:
                    click.echo("Strict mode: Stopping due to validation failures.", err=True)
                    sys.exit(1)
            
            if len(valid_rooms) == 0:
                click.echo("Error: No valid rooms to process.", err=True)
                sys.exit(1)
            
        except ImportError as e:
            click.echo(f"Error: Missing parser module: {e}", err=True)
            sys.exit(2)
        except Exception as e:
            click.echo(f"Error: Failed to parse or validate CSV: {e}", err=True)
            sys.exit(2)
        
        if dry_run:
            click.echo("Dry run mode: Configuration and CSV validation completed successfully.")
            click.echo(f"Ready to process {len(valid_rooms)} valid rooms.")
            click.echo("No PDFs were generated.")
            return
        
        # Phase 3: Layout Engine - Compute geometric layouts
        if verbose:
            click.echo("Computing geometric layouts...")
        
        try:
            from src.layout import ParametricLayoutEngine
            
            # Initialize layout engine
            layout_engine = ParametricLayoutEngine(config_dict)
            
            # Compute layouts for all valid rooms
            computed_layouts = []
            layout_errors = 0
            
            for room_data in valid_rooms:
                try:
                    if verbose:
                        click.echo(f"  Computing layout for {room_data.room_id}...")
                    
                    layout_result = layout_engine.compute_layout(room_data, config_dict)
                    computed_layouts.append(layout_result)
                    
                    # Check for layout validation errors
                    if not layout_result.validation_result.is_valid:
                        layout_errors += 1
                        if verbose:
                            click.echo(f"    Warning: Layout validation failed for {room_data.room_id}")
                            for error in layout_result.validation_result.errors:
                                click.echo(f"      {error.field}: {error.message}")
                    
                    elif verbose:
                        click.echo(f"    ✓ Layout computed: {layout_result.total_width:.1f}\" × {layout_result.total_depth:.1f}\"")
                        click.echo(f"      Modules: {len(layout_result.modules)}, Fillers: {len(layout_result.fillers)}")
                        if layout_result.ada_layout:
                            click.echo(f"      ADA compliance: {layout_result.ada_layout.code_basis}")
                
                except Exception as e:
                    layout_errors += 1
                    click.echo(f"Error computing layout for {room_data.room_id}: {e}", err=True)
                    if verbose:
                        import traceback
                        traceback.print_exc()
            
            # Report layout computation results
            successful_layouts = len(computed_layouts) - layout_errors
            if verbose or layout_errors > 0:
                click.echo(f"Layout Computation Summary:")
                click.echo(f"  Total rooms: {len(valid_rooms)}")
                click.echo(f"  Successful layouts: {successful_layouts}")
                click.echo(f"  Failed layouts: {layout_errors}")
                if layout_errors > 0:
                    click.echo(f"  Success rate: {successful_layouts/len(valid_rooms)*100:.1f}%")
            
            if layout_errors > 0:
                click.echo(f"Warning: {layout_errors} rooms failed layout computation.", err=True)
                if strict:
                    click.echo("Strict mode: Stopping due to layout failures.", err=True)
                    sys.exit(1)
            
            if len(computed_layouts) == 0:
                click.echo("Error: No valid layouts to render.", err=True)
                sys.exit(1)
            
        except ImportError as e:
            click.echo(f"Error: Missing layout engine module: {e}", err=True)
            sys.exit(2)
        except Exception as e:
            click.echo(f"Error: Failed to compute layouts: {e}", err=True)
            sys.exit(2)
        
        # Phase 4: PDF Rendering - Generate shop drawings
        if not dry_run:
            if verbose:
                click.echo("Generating PDF shop drawings...")
            
            try:
                from src.renderer.pdf_renderer import PDFRenderer
                from src.renderer.drawing_generator import ShopDrawingGenerator
                
                # Initialize PDF renderer with configuration
                scale = config_dict.get("SCALE_PLAN", 0.25)
                margins = config_dict.get("PDF", {}).get("MARGINS", [0.5, 0.5, 0.5, 0.5])
                renderer = PDFRenderer(scale=scale, margins=margins)
                
                # Initialize drawing generator
                drawing_generator = ShopDrawingGenerator(renderer, config_dict)
                
                # Generate PDFs for all valid layouts
                generated_pdfs = []
                pdf_errors = 0
                
                for layout in computed_layouts:
                    try:
                        if verbose:
                            click.echo(f"  Generating PDF for {layout.room_id}...")
                        
                        pdf_path = drawing_generator.generate_shop_drawing(layout, output)
                        generated_pdfs.append(pdf_path)
                        
                        if verbose:
                            click.echo(f"    ✓ PDF generated: {pdf_path}")
                    
                    except Exception as e:
                        pdf_errors += 1
                        click.echo(f"Error generating PDF for {layout.room_id}: {e}", err=True)
                        if verbose:
                            import traceback
                            traceback.print_exc()
                
                # Report PDF generation results
                successful_pdfs = len(generated_pdfs)
                if verbose or pdf_errors > 0:
                    click.echo(f"PDF Generation Summary:")
                    click.echo(f"  Total layouts: {len(computed_layouts)}")
                    click.echo(f"  Successful PDFs: {successful_pdfs}")
                    click.echo(f"  Failed PDFs: {pdf_errors}")
                    if pdf_errors > 0:
                        click.echo(f"  Success rate: {successful_pdfs/len(computed_layouts)*100:.1f}%")
                
                if pdf_errors > 0:
                    click.echo(f"Warning: {pdf_errors} PDFs failed to generate.", err=True)
                    if strict:
                        click.echo("Strict mode: Stopping due to PDF generation failures.", err=True)
                        sys.exit(1)
                
            except ImportError as e:
                click.echo(f"Error: Missing PDF renderer module: {e}", err=True)
                sys.exit(2)
            except Exception as e:
                click.echo(f"Error: Failed to generate PDFs: {e}", err=True)
                sys.exit(2)
        
        # Success message
        click.echo(f"✓ Configuration loaded and validated")
        click.echo(f"✓ CSV data parsed and validated: {len(valid_rooms)} valid rooms")
        click.echo(f"✓ Geometric layouts computed: {successful_layouts} successful layouts")
        if not dry_run:
            click.echo(f"✓ PDF shop drawings generated: {len(generated_pdfs)} files")
        click.echo(f"✓ Output directory prepared: {output}")
        click.echo(f"✓ Error reports written to: {output}/logs/")
        
        if dry_run:
            click.echo("Dry run complete - no PDFs generated.")
        else:
            click.echo("Phase 4 implementation complete! Shop drawings ready for review.")
        
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.", err=True)
        sys.exit(130)
    
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)


@click.group()
def cli():
    """Millwork Drafter command line tools."""
    pass


@cli.command()
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default="config/default.yaml",
    help="Output path for the configuration file"
)
def init_config(output: Path):
    """Initialize a new configuration file with defaults."""
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        
        if output.exists():
            if not click.confirm(f"Configuration file {output} already exists. Overwrite?"):
                click.echo("Operation cancelled.")
                return
        
        # Create default configuration
        default_config = MillworkConfig()
        
        from src.core.config import save_config_to_yaml
        save_config_to_yaml(default_config, str(output))
        
        click.echo(f"✓ Default configuration created: {output}")
        click.echo("Edit this file to customize settings for your project.")
        
    except Exception as e:
        click.echo(f"Error creating configuration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("config_path", type=click.Path(exists=True, path_type=Path))
def validate_config(config_path: Path):
    """Validate a configuration file."""
    try:
        config_loader = ConfigLoader()
        config_dict = config_loader.load_config(str(config_path))
        config_hash = config_loader.get_config_hash(config_dict)
        
        click.echo(f"✓ Configuration is valid: {config_path}")
        click.echo(f"Configuration hash: {config_hash}")
        
    except Exception as e:
        click.echo(f"✗ Configuration validation failed: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    # Support both direct execution and CLI group
    if len(sys.argv) == 1:
        # No arguments - show help
        main(["--help"])
    elif sys.argv[1] in ["init-config", "validate-config"]:
        # CLI subcommands
        cli()
    else:
        # Main generation command
        main()