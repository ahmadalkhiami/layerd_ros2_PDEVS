#!/usr/bin/env python3
"""
Validation runner for ROS2 DEVS simulation.
Provides easy-to-use validation commands with different levels and reporting.
"""

import sys
import os
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulation.enhanced_validator import EnhancedValidator, ValidationLevel
from core.trace import trace_logger
from simulation.config import SimulationConfig

class ValidationRunner:
    """Runner for comprehensive validation of ROS2 DEVS models"""
    
    def __init__(self):
        self.validators = {
            ValidationLevel.BASIC: EnhancedValidator(ValidationLevel.BASIC),
            ValidationLevel.STANDARD: EnhancedValidator(ValidationLevel.STANDARD),
            ValidationLevel.COMPREHENSIVE: EnhancedValidator(ValidationLevel.COMPREHENSIVE)
        }
    
    def run_validation(self, 
                      traces: List[Dict], 
                      level: ValidationLevel = ValidationLevel.STANDARD,
                      output_dir: str = "validation_results",
                      save_results: bool = True,
                      print_summary: bool = True) -> Dict[str, Any]:
        """
        Run validation with specified parameters
        
        Args:
            traces: Simulation traces to validate
            level: Validation level (basic, standard, comprehensive)
            output_dir: Directory to save results
            save_results: Whether to save results to file
            print_summary: Whether to print summary to console
            
        Returns:
            Validation results dictionary
        """
        print(f"🔍 Running {level.value} validation...")
        print(f"📊 Analyzing {len(traces)} trace events")
        
        # Run validation
        validator = self.validators[level]
        results = validator.validate(traces)
        
        # Print summary if requested
        if print_summary:
            validator.print_summary()
        
        # Save results if requested
        if save_results:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # Save detailed results
            results_file = output_path / f"validation_results_{level.value}.json"
            validator.save_results(str(results_file))
            
            # Save summary report
            summary_file = output_path / f"validation_summary_{level.value}.txt"
            self._save_summary_report(results, str(summary_file))
            
            print(f"📄 Results saved to: {output_path}")
        
        return results
    
    def _save_summary_report(self, results: Dict[str, Any], filepath: str):
        """Save a human-readable summary report"""
        with open(filepath, 'w') as f:
            f.write("ROS2 DEVS Validation Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Validation Level: {results['validation_level']}\n")
            f.write(f"Total Rules: {results['total_rules']}\n")
            f.write(f"Passed: {results['passed_rules']} ✅\n")
            f.write(f"Failed: {results['failed_rules']} ❌\n")
            f.write(f"Success Rate: {results['summary']['success_rate']:.1%}\n\n")
            
            f.write("Results by Category:\n")
            f.write("-" * 30 + "\n")
            for category, stats in results['summary']['categories'].items():
                f.write(f"{category}: {stats['passed']}/{stats['total']} passed\n")
            
            f.write("\nFailed Checks:\n")
            f.write("-" * 30 + "\n")
            for result in results['results']:
                if not result['passed']:
                    f.write(f"- {result['rule_name']}: {result['message']}\n")
    
    def run_comprehensive_validation(self, traces: List[Dict], output_dir: str = "validation_results") -> Dict[str, Any]:
        """Run all validation levels and compare results"""
        print("🚀 Running comprehensive validation across all levels...")
        
        all_results = {}
        
        for level in ValidationLevel:
            print(f"\n{'='*60}")
            print(f"Running {level.value.upper()} validation")
            print(f"{'='*60}")
            
            results = self.run_validation(
                traces=traces,
                level=level,
                output_dir=output_dir,
                save_results=True,
                print_summary=True
            )
            
            all_results[level.value] = results
        
        # Generate comparison report
        self._generate_comparison_report(all_results, output_dir)
        
        return all_results
    
    def _generate_comparison_report(self, all_results: Dict[str, Dict], output_dir: str):
        """Generate a comparison report across all validation levels"""
        comparison_file = Path(output_dir) / "validation_comparison.txt"
        
        with open(comparison_file, 'w') as f:
            f.write("ROS2 DEVS Validation Comparison Report\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("Summary by Validation Level:\n")
            f.write("-" * 40 + "\n")
            
            for level, results in all_results.items():
                f.write(f"\n{level.upper()}:\n")
                f.write(f"  Total Rules: {results['total_rules']}\n")
                f.write(f"  Passed: {results['passed_rules']}\n")
                f.write(f"  Failed: {results['failed_rules']}\n")
                f.write(f"  Success Rate: {results['summary']['success_rate']:.1%}\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("RECOMMENDATIONS:\n")
            f.write("=" * 60 + "\n")
            
            # Generate recommendations based on results
            basic_results = all_results.get('basic', {})
            comprehensive_results = all_results.get('comprehensive', {})
            
            if basic_results.get('summary', {}).get('success_rate', 0) < 0.8:
                f.write("⚠️  Basic validation shows significant issues. Review model structure.\n")
            
            if comprehensive_results.get('summary', {}).get('success_rate', 0) < 0.6:
                f.write("❌ Comprehensive validation reveals critical issues. Model needs major improvements.\n")
            
            if comprehensive_results.get('summary', {}).get('success_rate', 0) > 0.9:
                f.write("✅ Model passes comprehensive validation. Ready for production use.\n")
            
            f.write("\nNext Steps:\n")
            f.write("1. Review failed validation checks\n")
            f.write("2. Address critical issues first\n")
            f.write("3. Re-run validation after fixes\n")
            f.write("4. Consider performance optimizations if needed\n")
        
        print(f"📊 Comparison report saved to: {comparison_file}")


def main():
    """Main entry point for validation runner"""
    parser = argparse.ArgumentParser(
        description="ROS2 DEVS Validation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run basic validation
  python validation_runner.py --level basic --traces traces.json
  
  # Run comprehensive validation with all levels
  python validation_runner.py --comprehensive --traces traces.json
  
  # Run validation and save detailed results
  python validation_runner.py --level standard --traces traces.json --output results/
        """
    )
    
    parser.add_argument(
        '--traces',
        type=str,
        help='Path to traces file (JSON)'
    )
    
    parser.add_argument(
        '--level',
        choices=['basic', 'standard', 'comprehensive'],
        default='standard',
        help='Validation level'
    )
    
    parser.add_argument(
        '--comprehensive',
        action='store_true',
        help='Run all validation levels and compare'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='validation_results',
        help='Output directory for results'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Don\'t save results to file'
    )
    
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Don\'t print summary to console'
    )
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = ValidationRunner()
    
    # Load traces
    traces = []
    if args.traces:
        try:
            with open(args.traces, 'r') as f:
                traces = json.load(f)
            print(f"📁 Loaded {len(traces)} traces from {args.traces}")
        except Exception as e:
            print(f"❌ Error loading traces: {e}")
            return 1
    else:
        print("❌ No traces file specified. Use --traces to specify a file.")
        return 1
    
    try:
        if args.comprehensive:
            # Run comprehensive validation
            results = runner.run_comprehensive_validation(traces, args.output)
        else:
            # Run single level validation
            level = ValidationLevel(args.level)
            results = runner.run_validation(
                traces=traces,
                level=level,
                output_dir=args.output,
                save_results=not args.no_save,
                print_summary=not args.no_summary
            )
        
        print("\n✅ Validation completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Validation error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 