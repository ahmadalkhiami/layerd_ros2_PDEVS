"""
Main entry point for ROS2 DEVS simulation.
"""

import argparse
import sys
import time
import os
from pathlib import Path

# Add parent directory to Python path to import from sibling directories
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pypdevs.simulator import Simulator
from core.trace import trace_logger
from simulation.config import SimulationConfig, ConfigPresets
from simulation import create_system
from simulation.validator import TraceValidator, PerformanceValidator
from simulation.enhanced_validator import EnhancedValidator, ValidationLevel
from simulation.analyzer import SimulationAnalyzer

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="ROS2 DEVS Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run dummy robot system
  python main.py --system dummy_robot

  # Run with custom configuration
  python main.py --config my_config.yaml
  
  # Run benchmark configuration
  python main.py --preset benchmark --time 60.0
        """
    )
    
    # System configuration
    parser.add_argument(
        '--system', 
        choices=['dummy_robot', 'minimal'],
        default='dummy_robot',
        help='System configuration to run'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Configuration file (YAML)'
    )
    
    parser.add_argument(
        '--preset',
        choices=['development', 'production', 'testing', 'benchmark'],
        help='Use configuration preset'
    )
    
    # Simulation parameters
    parser.add_argument(
        '--time',
        type=float,
        default=10.0,
        help='Simulation time in seconds'
    )
    
    parser.add_argument(
        '--time-scale',
        type=float,
        default=1.0,
        help='Time scale factor (1.0 = real-time, 2.0 = 2x speed)'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir',
        type=str,
        default='.',
        help='Output directory for traces and analysis'
    )
    
    parser.add_argument(
        '--trace-file',
        type=str,
        default='ros2_trace.log',
        help='Trace output file'
    )
    
    parser.add_argument(
        '--no-console',
        action='store_true',
        help='Disable console output'
    )
    
    # Analysis options
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate simulation results'
    )
    
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Analyze simulation results'
    )
    
    return parser.parse_args()

def configure_simulation(args):
    """Configure simulation based on arguments"""
    global config
    
    # Load configuration
    if args.config:
        config = SimulationConfig.from_yaml(args.config)
    elif args.preset:
        preset_map = {
            'development': ConfigPresets.development,
            'production': ConfigPresets.production,
            'testing': ConfigPresets.testing,
            'benchmark': ConfigPresets.benchmark
        }
        config = preset_map[args.preset]()
    else:
        # Default configuration for dummy robot
        config = SimulationConfig()
        config.enable_map_server = True
        config.enable_robot_state_publisher = True
        config.enable_joint_state_publisher = True
        config.enable_laser_scanner = True
        config.enable_parameter_services = True
        config.enable_diagnostics = True
    
    # Override with command line arguments
    config.simulation_time_seconds = args.time
    config.time_scale = args.time_scale
    
    # Configure logging
    config.logging.trace_file_path = args.trace_file
    config.logging.trace_to_console = not args.no_console
    
    # Apply configuration
    if config.logging.trace_to_file:
        trace_logger.enable_file_output(config.logging.trace_file_path)
    trace_logger.console_output = config.logging.trace_to_console

def run_simulation(args):
    """Run the simulation"""
    print("="*60)
    print("ROS2 DEVS Simulation")
    print("="*60)
    print(f"System: {args.system}")
    print(f"Duration: {config.simulation_time_seconds}s")
    print(f"Time Scale: {config.time_scale}x")
    print(f"Features:")
    print(f"  - Map Server: {config.enable_map_server}")
    print(f"  - Robot State Publisher: {config.enable_robot_state_publisher}")
    print(f"  - Joint State Publisher: {config.enable_joint_state_publisher}")
    print(f"  - Laser Scanner: {config.enable_laser_scanner}")
    print(f"  - Parameter Services: {config.enable_parameter_services}")
    print(f"  - Diagnostics: {config.enable_diagnostics}")
    print("="*60)
    
    # Create system
    print("\nCreating system...")
    system = create_system(args.system)
    
    # Create simulator
    print("Initializing simulator...")
    sim = Simulator(system)
    sim.setClassicDEVS()
    
    # Run simulation
    print(f"\nRunning simulation for {config.simulation_time_seconds} seconds...")
    start_time = time.time()
    
    sim.setTerminationTime(config.simulation_time_seconds)
    sim.simulate()
    
    elapsed_time = time.time() - start_time
    print(f"\nSimulation completed in {elapsed_time:.2f} seconds")
    print(f"Simulation/Real-time ratio: {config.simulation_time_seconds/elapsed_time:.2f}x")
    
    # Get traces
    traces = trace_logger.events
    print(f"\nGenerated {len(traces)} trace events")
    
    return traces

def validate_simulation(traces):
    """Validate simulation results"""
    print("\nValidating simulation results...")
    
    # Create enhanced validator
    validator = EnhancedValidator(ValidationLevel.STANDARD)
    
    # Run validation
    results = validator.validate(traces)
    
    # Print summary
    validator.print_summary()
    
    # Save results
    validator.save_results("validation_results.json")
    
    if results["failed_rules"] == 0:
        print("✅ Validation passed")
    else:
        print("❌ Validation failed")
        print(f"  - {results['failed_rules']} validation errors found")

def analyze_simulation(traces, output_dir):
    """Analyze simulation results"""
    print("\nAnalyzing simulation results...")
    
    # Create analyzer
    analyzer = SimulationAnalyzer()
    
    # Run analysis
    analyzer.analyze(traces)
    
    # Save results
    analyzer.save_results(output_dir)
    
    print("✅ Analysis complete")

def main():
    """Main entry point"""
    args = parse_args()
    
    try:
        # Configure simulation
        configure_simulation(args)
        
        # Run simulation
        traces = run_simulation(args)
        
        # Save traces in ROS2-compatible format
        trace_logger.save_traces(f"{args.output_dir}/ros2_traces.csv")
        
        # Validate if requested
        if args.validate:
            validate_simulation(traces)
            
        # Analyze if requested
        if args.analyze:
            analyze_simulation(traces, args.output_dir)
            
        print("\n✅ Simulation completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Simulation interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\n\n❌ Simulation error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())