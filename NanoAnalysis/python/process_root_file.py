import ROOT
import sys
import argparse
from ROOT import TEfficiency

def get_genEventSumw(input_file, maxEntriesPerSample=None):
    '''Util function to get the sum of weights per event. Returns the sum of weights'''
    f = ROOT.TFile.Open(input_file, "READ")

    runs  = f.Runs
    event = f.Events
    nRuns = runs.GetEntries()
    nEntries = event.GetEntries()

    iRun = 0
    genEventCount = 0
    genEventSumw = 0.

    while iRun < nRuns and runs.GetEntry(iRun) :
        genEventCount += runs.genEventCount
        genEventSumw += runs.genEventSumw
        iRun +=1
    print ("gen=", genEventCount, "sumw=", genEventSumw)

    if maxEntriesPerSample is not None:
        print(f"Scaling to {maxEntriesPerSample} entries")
        if nEntries>maxEntriesPerSample :
            genEventSumw = genEventSumw*maxEntriesPerSample/nEntries
            nEntries=maxEntriesPerSample
        print("    scaled to:", nEntries, "sumw=", genEventSumw)

    return genEventSumw

def getEff(tot, sel):
    eff = sel/tot
    up = TEfficiency.ClopperPearson(tot, sel, 0.683, True)
    dn = TEfficiency.ClopperPearson(tot, sel, 0.683, False)
    return eff, up-eff, eff-dn

def identify_prescaled_triggers(root_file, tree_name="Events"):
    """
    Counts how many events that passed 'HLT_AK8PFJet420_TrimMass30' also passed 'HLT_AK8PFJet400_TrimMass30'.
    
    Args:
        root_file (str): Path to the .root file containing the tree with events.
        tree_name (str): Name of the tree in the ROOT file (default: "Events").
    
    Returns:
        int: The number of events that passed both triggers.
    """
    # Open the .root file
    file = ROOT.TFile.Open(root_file, "READ")
    if not file or file.IsZombie():
        print(f"Error: Unable to open the file {root_file}")
        return 0

    # Get the tree named Events
    tree = file.Get(tree_name)
    if not tree:
        print(f"Error: Tree '{tree_name}' not found in the file.")
        file.Close()
        return 0

    # Initialize counters
    passed_both = 0

    # Loop through the events in the tree
    for event in tree:
        # Check if the event passed both triggers
        if getattr(event, "HLT_AK8PFJet420_TrimMass30") and getattr(event, "HLT_AK8PFJet400_TrimMass30"):
            passed_both += 1

    # Close the file
    file.Close()

    return passed_both


def filter_events(trigger_file, root_file, tree_name="Events"):
    """
    Filters events in a ROOT tree based on a list of triggers and calculates statistics.
    
    Args:
        trigger_file (str): Path to the .txt file containing the list of triggers.
        root_file (str): Path to the .root file containing the tree with events.
        tree_name (str): Name of the tree in the ROOT file (default: "Events").
    
    Returns:
        dict: A dictionary with total events, selected events, and percentage passing.
    """
    # Read the list of triggers from the .txt file
    with open(trigger_file, 'r') as f:
        triggers = [line.strip() for line in f if line.strip()]
    
    if not triggers:
        raise ValueError("The trigger file is empty or contains only whitespace.")
    print(triggers)
    
    # Open the .root file
    file = ROOT.TFile.Open(root_file, "READ")
    if not file or file.IsZombie():
        print(f"Error: Unable to open the file {root_file}")
        return

    # Get the tree named Events
    tree = file.Get(tree_name)
    if not tree:
        print(f"Error: Tree '{tree_name}' not found in the file.")
        file.Close()
        return

    # Initialize counters for total events and passed events
    total_events = 0
    passed_events_count = 0
    weighted_events = 0.0
    # Loop through the events in the tree
    for event in tree:
        total_events += 1
        # Check if any of the triggers are true for this event
        passed = False
        for trigger in triggers:
            if getattr(event, trigger):  # Check if the trigger variable is True for this event
                passed = True
                break
        if passed and getattr(event, "HLT_passZZ4l") == 1 :
            passed_events_count += 1
            weighted_events += getattr(event, "overallEventWeight")


    # Calculate the percentage of events that passed
    percentage = (passed_events_count / total_events) * 100 if total_events > 0 else 0
    # Calculate the efficiency
    efficiency, eff_up, eff_down = getEff(total_events, passed_events_count)
    # Print the statistics
    print(f"Total events: {total_events}")
    print(f"Events passing the triggers: {passed_events_count}")
    print(f"Percentage passing: {percentage:.2f}%")
    print(f"Efficiency passing: {efficiency:.2f}%, {eff_up:.2f}%, {eff_down:.2f}%")
    print(f"Weighted events passing the triggers: {weighted_events:.2f}")

    # Return the statistics in a dictionary
    stats = {
        "total_events": total_events,
        "passed_events": passed_events_count,
        "percentage": percentage
    }

    file.Close()
    return stats, weighted_events


def process_root_file(input_file):
    # Open the .root file
    file = ROOT.TFile.Open(input_file, "READ")
    if not file or file.IsZombie():
        print(f"Error: Unable to open the file {input_file}")
        return

    # Get the tree named Events
    tree = file.Get("Events")
    if not tree:
        print("Error: Tree 'Events' not found in the file.")
        file.Close()
        return

    # Dictionary to count the number of events with HLT branches set to True
    hlt_counts = {}

    # Initialize counters for all HLT_* branches
    branches = tree.GetListOfBranches()
    for branch in branches:
        branch_name = branch.GetName()
        if branch_name.startswith("HLT_"):
            hlt_counts[branch_name] = 0

    # Loop over the events in the tree
    for event in tree:
        for branch_name in hlt_counts.keys():
            value = getattr(event, branch_name, None)
            if value:  # If the HLT branch is True
                hlt_counts[branch_name] += 1

    # Print the results
    print("Number of events with each HLT branch activated:")
    for branch_name, count in hlt_counts.items():
        #print(f"{branch_name}: {count}")
        print(f"{count}")


    # Close the file
    file.Close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py input_file.root")
        sys.exit(1)

    input_file = sys.argv[1]
    stats, weighted_events= filter_events("../data/list_HLT_JETMET.txt", input_file)
    genEventSumw = get_genEventSumw(input_file)
    print("Weighted events", weighted_events/genEventSumw)
    print("Eff_weighted", getEff(genEventSumw,weighted_events))
    #prescaled_events = identify_prescaled_triggers(input_file)
    #print(stats, "prescaled triggers")
    #process_root_file(input_file)
