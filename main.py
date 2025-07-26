"""
Main entry point for ROS2 DEVS simulation.
"""

import argparse
import sys
import time
from pathlib import Path

from pypdevs.simulator import Simulator

from core import (
    config, ConfigPresets, SimulationConfig,
    trace_logger, context_manager
)
from simulation import (
    create_system,
    TraceValidator, PerformanceValidator,
    SimulationAnalyzer
)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="ROS2 DEVS Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run minimal system for 10 seconds
  python main.py --system minimal --time 10.0
  
  # Run full system with lifecycle nodes
  python main.py --system full --enable-lifecycle
  
  # Run with custom configuration
  python main.py --config my_config.yaml
  
  # Run benchmark configuration
  python main.py --preset benchmark --time 60.0
        """
    )
    
    # System configuration
    parser.add_argument(
        '--system', 
        choices=['minimal', 'full'],
        default='full',
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
    
    # Feature flags
    parser.add_argument(
        '--enable-lifecycle',
        action='store_true',
        help='Enable lifecycle nodes'
    )
    
    parser.add_argument(
        '--enable-actions',
        action='store_true',
        help='Enable action servers/clients'
    )
    
    parser.add_argument(
        '--disable-services',
        action='store_true',
        help='Disable service simulation'
    )
    
    # Output options
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
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Run validation after simulation'
    )
    
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Run analysis and generate plots'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Output directory for results'
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
    
    # Override with command line arguments
    config.simulation_time_seconds = args.time
    config.time_scale = args.time_scale
    
    if args.enable_lifecycle:
        config.enable_lifecycle_nodes = True
    if args.enable_actions:
        config.enable_actions = True
    if args.disable_services:
        config.enable_services = False
        
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
    print(f"  - Lifecycle Nodes: {config.enable_lifecycle_nodes}")
    print(f"  - Actions: {config.enable_actions}")
    print(f"  - Services: {config.enable_services}")
    print("="*60)
    
    # Create system
    print("\nCreating system...")
    system = create_system(args.system)
    
    # Create simulator
    print("Initializing simulator...")
    sim = Simulator(system)
    sim.setClassicDEVS()
    
    # Set verbosity if in development mode
    if config.logging.default_log_level == "DEBUG":
        sim.setVerbose()
    
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
    """Run validation on simulation traces"""
    print("\n" + "="*60)
    print("Running Validation")
    print("="*60)
    
    # Run trace validation
    validator = TraceValidator()
    checks = validator.validate_all(traces)
    
    print(validator.generate_report())
    
    # Run performance validation
    perf_validator = PerformanceValidator()
    perf_metrics = perf_validator.analyze_performance(traces)
    
    print("\nPerformance Metrics:")
    print("-"*30)
    
    if 'message_latency' in perf_metrics:
        latency = perf_metrics['message_latency']
        print(f"Message Latency:")
        print(f"  Average: {latency['average_ms']:.2f}ms")
        print(f"  Min: {latency['min_ms']:.2f}ms")
        print(f"  Max: {latency['max_ms']:.2f}ms")
        print(f"  95th percentile: {latency['p95_ms']:.2f}ms")
        
    if 'throughput' in perf_metrics:
        print(f"\nThroughput by Topic:")
        for topic, stats in perf_metrics['throughput'].items():
            print(f"  {topic}: {stats['rate_hz']:.1f} Hz")
            
    return checks, perf_metrics


def analyze_simulation(traces, output_dir):
    """Run analysis and generate plots"""
    print("\n" + "="*60)
    print("Running Analysis")
    print("="*60)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create analyzer
    analyzer = SimulationAnalyzer()
    analyzer.load_traces(traces)
    
    # Generate summary
    print(analyzer.generate_summary())
    
    # Save summary to file
    with open(output_path / "summary.txt", 'w') as f:
        f.write(analyzer.generate_summary())
    
    # Generate plots
    print("\nGenerating plots...")
    
    try:
        analyzer.plot_event_timeline(output_path / "event_timeline.png")
        print("  - Event timeline saved")
    except Exception as e:
        print(f"  - Error generating event timeline: {e}")
        
    try:
        analyzer.plot_message_latency_distribution(output_path / "latency_distribution.png")
        print("  - Latency distribution saved")
    except Exception as e:
        print(f"  - Error generating latency distribution: {e}")
        
    try:
        analyzer.plot_throughput_over_time(save_path=output_path / "throughput.png")
        print("  - Throughput plot saved")
    except Exception as e:
        print(f"  - Error generating throughput plot: {e}")
        
    # Export to CSV
    analyzer.export_to_csv(output_path / "traces.csv")
    print(f"\nResults saved to: {output_path}")


def main():
    """Main entry point"""
    args = parse_args()
    
    try:
        # Configure simulation
        configure_simulation(args)
        
        # Run simulation
        traces = run_simulation(args)
        
        # Save traces
        trace_logger.save_json(f"{args.output_dir}/traces.json")
        
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