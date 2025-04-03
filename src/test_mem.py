from memory_analysis.memory_capture import MemoryCapture
from memory_analysis.process_analyzer import ProcessAnalyzer
import json

def display_menu():
    print("\nMemory Analysis Options:")
    print("1. View Top Processes")
    print("2. View System Memory Stats")
    print("3. View Processes by Category")
    print("4. Analyze Specific Process")
    print("5. Exit")
    return input("Select option (1-5): ")

def main():
    mem_capture = MemoryCapture()
    proc_analyzer = ProcessAnalyzer()

    while True:
        choice = display_menu()
        
        if choice == '1':
            processes = proc_analyzer.get_running_processes()
            sorted_processes = sorted(processes, 
                                   key=lambda x: x['memory_usage'], 
                                   reverse=True)[:10]
            print("\nTop 10 Processes by Memory Usage:")
            for idx, proc in enumerate(sorted_processes, 1):
                print(f"{idx}. {proc['name']} (PID: {proc['pid']}) - {proc['memory_usage']}MB")
        
        elif choice == '2':
            mem_info = mem_capture.get_system_memory_info()
            print("\nSystem Memory Statistics:")
            print(json.dumps(mem_info, indent=2))
        
        elif choice == '3':
            categories = list(proc_analyzer.process_categories.keys())
            print("\nAvailable categories:", ', '.join(categories))
            cat = input("Enter category: ")
            processes = proc_analyzer.get_processes_by_category(cat)
            print(f"\nProcesses in category '{cat}':")
            for proc in processes:
                print(f"{proc['name']} (PID: {proc['pid']}) - {proc['memory_usage']}MB")
        
        elif choice == '4':
            pid = input("Enter PID to analyze: ")
            try:
                analysis = proc_analyzer.analyze_process(int(pid))
                if analysis:
                    print(json.dumps(analysis, indent=2))
            except ValueError:
                print("Invalid PID")
        
        elif choice == '5':
            break

if __name__ == "__main__":
    main()