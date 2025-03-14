# Causal Ordering Simulation Programs

This repository contains three Python simulation programs that demonstrate causal ordering using different clock algorithms. Each program uses a Tkinter-based graphical user interface (GUI) to visualize the progress of events on horizontal timelines for three processes (P1, P2, and P3).

---

## Programs Included

1. **BSS.py**  
   - Implements the Birman–Schiper–Stephenson (BSS) algorithm using vector clocks.
   - Demonstrates causal ordering with buffering.
   - Displays vector clocks in the form `[1, 0, 0]`.

2. **matrix_clock.py**  
   - Implements causal ordering using matrix clocks (unicast) with buffering.
   - Each process maintains a 2D matrix clock.
   - The full matrix is displayed for every send/receive event with sufficient spacing.

3. **SES.py**  
   - Implements the Schiper–Eggli–Sandoz (SES) algorithm with buffering.
   - Uses vector clocks with a full merge on receive.
   - Displays the updated clock as a simple list.

4. **DistributedChatMatrix.py (Bonus)**  
   - Simulates a real-world distributed chat application using matrix clocks.
   - Each process is displayed as its own chat panel showing full matrix clocks (as multi-line strings) along with sent and received messages.
   - Demonstrates causal ordering with buffering in a more realistic, interactive chat interface.
   - Includes a scenario where one message is intentionally buffered and later delivered.


---

## Prerequisites

- **Python 3.6 or higher** is recommended.
- These programs use the built-in **Tkinter** library for GUI visualization.
  - On **Windows** and **macOS**, Tkinter is usually bundled with Python.
  - On **Linux**, you might need to install it separately (for example, on Ubuntu/Debian run:  
    `sudo apt-get install python3-tk`).

---

## Setup and Installation

1. **Download or clone this repository** to your local machine.

2. **Ensure Python 3 is installed.**  
   To check your Python version, run:
   ```bash
   python3 --version
   ```
   or
   ```bash
   python --version
   ```

3. **(Optional) Create a virtual environment** if desired:
   ```bash
   python3 -m venv venv
   source venv/bin/activate      # On Linux/macOS
   venv\Scripts\activate         # On Windows
   ```

4. **No additional dependencies are required**, as Tkinter is part of the standard library.

---

## Running the Simulations

Each simulation is a stand-alone Python script. Open a terminal in the repository folder and run the desired simulation:

- **BSS Simulation:**
  ```bash
  python BSS.py
  ```
- **Matrix Clock Simulation:**
  ```bash
  python matrix_clock.py
  ```
- **SES Simulation:**
  ```bash
  python SES.py
  ```

- **Bonus task Simulation:**
  ```bash
  python DistributedApp.py
  ```

> **Note:** Depending on your system, you may need to use `python3` instead of `python`.

---

## How to Interact with the Simulation

Each simulation window will display:

- **Horizontal timelines** for processes P1, P2, and P3.
- **Graphical events:**
  - **Send events** are shown as yellow circles with a clock (or matrix) snapshot displayed underneath.
  - **Receive events** are shown as light green circles with the delivered clock (or matrix) snapshot.
  - **Arrows** indicate the send-to-receive relationship.
- **Matrix clocks (for matrix_clock.py)** are displayed as multi-line strings with extra spacing to avoid overlapping the timeline.

### Controls

- **Next Step Button:**  
  Click this button to execute the next event (send or receive) in the simulation. The event description will be logged in a text area below the timeline.
  
- **Reset Button:**  
  Click this button to reset the simulation to its initial state. All drawings and logs will be cleared, and the simulation will restart.

---

## Customizing the Simulations

- **Event List:**  
  Each simulation script contains an `events` list that specifies the sequence of send and receive events. You can modify or extend this list to test different scenarios or simulate different ordering behaviors.

- **Graphical Adjustments:**  
  The programs are configured with predefined offsets (such as `BASE_X`, `X_SPACING`, and vertical offsets in the `update_vector_display()` methods) to prevent overlapping of texts and timelines. Adjust these values in the code if you need further customization.

---

## Troubleshooting

- **Tkinter Errors:**  
  If you encounter an error related to Tkinter, ensure that Tkinter is installed on your system. On Linux, install it via your package manager (e.g., `sudo apt-get install python3-tk`).

- **Python Version:**  
  Verify that you are using Python 3, as the code may not be compatible with Python 2.

---

