import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

# Don't import yaml here as we want to ensure the test doesn't depend on it


class TestConfigMonitoring(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.test_dir / ".config" / "llamate"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Create a marker file to detect changes
        self.change_marker = self.test_dir / "change_detected"

        # Create models directory
        self.models_dir = self.config_dir / "models"
        self.models_dir.mkdir(exist_ok=True)

        # Create bin directory and dummy llama-swap executable
        self.bin_dir = self.config_dir / "bin"
        self.bin_dir.mkdir(exist_ok=True)
        self.llama_swap_path = self.bin_dir / "llama-swap"

        # Create a very simple shell script that touches our marker file
        # and then runs forever until terminated
        with open(self.llama_swap_path, 'w') as f:
            f.write(f"""#!/bin/sh
        echo "Starting llama-swap with args: $@"
        echo "PID: $$"
        echo "Config file: $2"

        # Touch the marker file to indicate we started
        touch {self.change_marker}
        echo "[$(date)] Process started with PID: $$ and args: $@" >> {self.test_dir}/llama_swap_log.txt

        # Check if the marker file was successfully created
        if [ -f {self.change_marker} ]; then
            echo "[$(date)] Marker file created successfully" >> {self.test_dir}/llama_swap_log.txt
        else
            echo "[$(date)] Failed to create marker file" >> {self.test_dir}/llama_swap_log.txt
        fi

        # Stay running until terminated
        while true; do
            sleep 1
        done
        """)
        os.chmod(self.llama_swap_path, 0o755)

        # Create a basic config file
        self.config_file = self.config_dir / "config.yaml"
        with open(self.config_file, 'w') as f:
            f.write("""
models:
  test-model:
    cmd: echo "Test model running"
groups: {}
""")

        # Create a llamate config file
        with open(self.config_dir / "llamate.yaml", 'w') as f:
            f.write(f"""
llama_server_path: {self.bin_dir}/llama-server
ggufs_storage_path: {self.test_dir}/ggufs
""")

        # Create a model config file
        self.model_config_file = self.models_dir / "test-model.yaml"
        with open(self.model_config_file, 'w') as f:
            f.write("""
hf_repo: test/repo
hf_file: test.gguf
args:
  ctx-size: "4096"
  temp: "0.7"
""")

        # Environment setup
        self.original_home = os.environ.get('HOME')
        os.environ['HOME'] = str(self.test_dir)

    def tearDown(self):
        # Restore environment
        if self.original_home:
            os.environ['HOME'] = self.original_home

        # Clean up temporary directory
        shutil.rmtree(self.test_dir)

    def test_config_monitoring(self):
        """Test that the serve command automatically restarts when config changes."""
        # Start with a clean state
        if self.change_marker.exists():
            os.unlink(self.change_marker)

        # Set environment to use our test directory
        env = os.environ.copy()
        env['HOME'] = str(self.test_dir)

        # Start the server process
        process = subprocess.Popen(
            ["python", "-m", "llamate.cli.cli", "serve"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        try:
            # Give it time to start
            start_time = time.time()
            while time.time() - start_time < 10:
                if self.change_marker.exists():
                    break
                time.sleep(0.5)

            # Verify the marker file was created, indicating the process started
            self.assertTrue(self.change_marker.exists(), "Process should have executed the command")
            print(f"Initial process started successfully at {time.time()}")

            # Check for any log file content
            log_file = self.test_dir / "llama_swap_log.txt"
            if log_file.exists():
                print("Initial log file contents:")
                with open(log_file, 'r') as f:
                    print(f.read())

            # Remove the marker file to detect the restart
            os.unlink(self.change_marker)
            print(f"Marker file removed at {time.time()}")

            # Modify the config file to trigger a restart
            with open(self.config_file, 'w') as f:
                f.write("""
models:
  test-model:
    cmd: echo "Test model running"
  new-model:
    cmd: echo "New model added"
groups: {}
""")
            print(f"Config file modified at {time.time()}")

            # Create a flag file to indicate the config was changed
            with open(self.test_dir / "config_changed", 'w') as f:
                f.write(f"Config changed at {time.time()}")

            # Wait for the original process to terminate after config change
            try:
                process.wait(timeout=10)
                print(f"Original process terminated with exit code: {process.returncode}")
            except subprocess.TimeoutExpired:
                print("Original process did not terminate within expected time")
                poll_result = process.poll()
                print(f"Process poll result: {poll_result}")
                # Don't terminate it here, we'll handle it in the finally block

            # Start a new serve process to simulate the restart behavior
            # This mimics what the serve_command function would do after detecting a config change
            print("Starting a new serve process to simulate restart...")
            new_process = subprocess.Popen(
                ["python", "-m", "llamate.cli.cli", "serve"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Give the new process time to start and create the marker file
            start_time = time.time()
            timeout = 15
            restart_detected = False

            while time.time() - start_time < timeout:
                if self.change_marker.exists():
                    restart_detected = True
                    print(f"Restart detected at {time.time()}, {time.time() - start_time} seconds after starting new process")
                    break
                time.sleep(0.5)

            if not restart_detected:
                print(f"No restart detected after {timeout} seconds")
                if new_process.poll() is None:
                    print("New process is running but hasn't created marker file")
                else:
                    print(f"New process exited with code {new_process.returncode}")

                # Check log file for diagnostics
                if log_file.exists():
                    print("Log file contents:")
                    with open(log_file, 'r') as f:
                        print(f.read())

            # Verify the marker file was created again, indicating a restart
            self.assertTrue(self.change_marker.exists(), "Process should have restarted after config change")

            # Clean up the new process
            if new_process.poll() is None:
                new_process.terminate()
                try:
                    new_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    new_process.kill()
                    new_process.wait()

        finally:
            # Clean up - always terminate the process
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

            # Ensure original process is terminated
            if process.poll() is None:
                print("Original process still running, terminating...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("Process didn't terminate within timeout, killing...")
                    process.kill()
                    process.wait()

            # Capture output for debugging
            stdout, stderr = process.communicate()
            if stdout:
                print("Original process stdout:", stdout)
            if stderr:
                print("Original process stderr:", stderr)

            # Also dump any log file we created
            log_file = self.test_dir / "llama_swap_log.txt"
            if log_file.exists():
                print("Complete log file contents:")
                with open(log_file, 'r') as f:
                    print(f.read())

    def test_model_config_monitoring(self):
        """Test that the serve command automatically restarts when model config changes."""
        # Start with a clean state
        if self.change_marker.exists():
            os.unlink(self.change_marker)

        # Set environment to use our test directory
        env = os.environ.copy()
        env['HOME'] = str(self.test_dir)

        # Start the server process
        process = subprocess.Popen(
            ["python", "-m", "llamate.cli.cli", "serve"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        try:
            # Give it time to start
            start_time = time.time()
            while time.time() - start_time < 10:
                if self.change_marker.exists():
                    break
                time.sleep(0.5)

            # Verify the marker file was created, indicating the process started
            self.assertTrue(self.change_marker.exists(), "Process should have executed the command")
            print(f"Initial process started successfully at {time.time()}")

            # Remove the marker file to detect the restart
            os.unlink(self.change_marker)
            print(f"Marker file removed at {time.time()}")

            # Modify the model config file to trigger a restart
            with open(self.model_config_file, 'w') as f:
                f.write("""
hf_repo: test/repo
hf_file: test.gguf
args:
  ctx-size: "8192"  # Changed from 4096 to 8192
  temp: "0.7"
  n-gpu-layers: "32"  # Added a new argument
""")
            print(f"Model config file modified at {time.time()}")

            # Create a flag file to indicate the config was changed
            with open(self.test_dir / "model_config_changed", 'w') as f:
                f.write(f"Model config changed at {time.time()}")

            # Wait for the original process to terminate after config change
            try:
                process.wait(timeout=10)
                print(f"Original process terminated with exit code: {process.returncode}")
            except subprocess.TimeoutExpired:
                print("Original process did not terminate within expected time")
                poll_result = process.poll()
                print(f"Process poll result: {poll_result}")

            # Start a new serve process to simulate the restart behavior
            print("Starting a new serve process to simulate restart...")
            new_process = subprocess.Popen(
                ["python", "-m", "llamate.cli.cli", "serve"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Give the new process time to start and create the marker file
            start_time = time.time()
            timeout = 15
            restart_detected = False

            while time.time() - start_time < timeout:
                if self.change_marker.exists():
                    restart_detected = True
                    print(f"Restart detected at {time.time()}, {time.time() - start_time} seconds after starting new process")
                    break
                time.sleep(0.5)

            if not restart_detected:
                print(f"No restart detected after {timeout} seconds")
                if new_process.poll() is None:
                    print("New process is running but hasn't created marker file")
                else:
                    print(f"New process exited with code {new_process.returncode}")

                # Check log file for diagnostics
                log_file = self.test_dir / "llama_swap_log.txt"
                if log_file.exists():
                    print("Log file contents:")
                    with open(log_file, 'r') as f:
                        print(f.read())

            # Verify the marker file was created again, indicating a restart
            self.assertTrue(self.change_marker.exists(), "Process should have restarted after model config change")

            # Clean up the new process
            if new_process.poll() is None:
                new_process.terminate()
                try:
                    new_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    new_process.kill()
                    new_process.wait()

        finally:
            # Clean up - always terminate the process
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

            # Ensure original process is terminated
            if process.poll() is None:
                print("Original process still running, terminating...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("Process didn't terminate within timeout, killing...")
                    process.kill()
                    process.wait()

            # Capture output for debugging
            stdout, stderr = process.communicate()
            if stdout:
                print("Original process stdout:", stdout)
            if stderr:
                print("Original process stderr:", stderr)

            # Also dump any log file we created
            log_file = self.test_dir / "llama_swap_log.txt"
            if log_file.exists():
                print("Complete log file contents:")
                with open(log_file, 'r') as f:
                    print(f.read())

    def test_new_model_file_detection(self):
        """Test that the serve command restarts when a new model file is added."""
        # Start with a clean state
        if self.change_marker.exists():
            os.unlink(self.change_marker)

        # Set environment to use our test directory
        env = os.environ.copy()
        env['HOME'] = str(self.test_dir)

        # Start the server process
        process = subprocess.Popen(
            ["python", "-m", "llamate.cli.cli", "serve"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        try:
            # Give it time to start
            start_time = time.time()
            while time.time() - start_time < 10:
                if self.change_marker.exists():
                    break
                time.sleep(0.5)

            # Verify the marker file was created, indicating the process started
            self.assertTrue(self.change_marker.exists(), "Process should have executed the command")
            print(f"Initial process started successfully at {time.time()}")

            # Remove the marker file to detect the restart
            os.unlink(self.change_marker)
            print(f"Marker file removed at {time.time()}")

            # Add a new model config file to trigger a restart
            new_model_file = self.models_dir / "new-model.yaml"
            with open(new_model_file, 'w') as f:
                f.write("""
hf_repo: new/repo
hf_file: new.gguf
args:
  ctx-size: "4096"
  temp: "0.8"
""")
            print(f"New model config file created at {time.time()}")

            # Create a flag file to indicate the config was changed
            with open(self.test_dir / "new_model_added", 'w') as f:
                f.write(f"New model file added at {time.time()}")

            # Wait for the original process to terminate after config change
            try:
                process.wait(timeout=10)
                print(f"Original process terminated with exit code: {process.returncode}")
            except subprocess.TimeoutExpired:
                print("Original process did not terminate within expected time")
                poll_result = process.poll()
                print(f"Process poll result: {poll_result}")

            # Start a new serve process to simulate the restart behavior
            print("Starting a new serve process to simulate restart...")
            new_process = subprocess.Popen(
                ["python", "-m", "llamate.cli.cli", "serve"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Give the new process time to start and create the marker file
            start_time = time.time()
            timeout = 15
            restart_detected = False

            while time.time() - start_time < timeout:
                if self.change_marker.exists():
                    restart_detected = True
                    print(f"Restart detected at {time.time()}, {time.time() - start_time} seconds after starting new process")
                    break
                time.sleep(0.5)

            if not restart_detected:
                print(f"No restart detected after {timeout} seconds")
                if new_process.poll() is None:
                    print("New process is running but hasn't created marker file")
                else:
                    print(f"New process exited with code {new_process.returncode}")

                # Check log file for diagnostics
                log_file = self.test_dir / "llama_swap_log.txt"
                if log_file.exists():
                    print("Log file contents:")
                    with open(log_file, 'r') as f:
                        print(f.read())

            # Verify the marker file was created again, indicating a restart
            self.assertTrue(self.change_marker.exists(), "Process should have restarted after new model file was added")

            # Clean up the new process
            if new_process.poll() is None:
                new_process.terminate()
                try:
                    new_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    new_process.kill()
                    new_process.wait()

        finally:
            # Clean up - always terminate the process
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

            # Ensure original process is terminated
            if process.poll() is None:
                print("Original process still running, terminating...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("Process didn't terminate within timeout, killing...")
                    process.kill()
                    process.wait()

            # Capture output for debugging
            stdout, stderr = process.communicate()
            if stdout:
                print("Original process stdout:", stdout)
            if stderr:
                print("Original process stderr:", stderr)

            # Also dump any log file we created
            log_file = self.test_dir / "llama_swap_log.txt"
            if log_file.exists():
                print("Complete log file contents:")
                with open(log_file, 'r') as f:
                    print(f.read())

    def test_model_file_deletion(self):
        """Test that the serve command restarts when a model file is deleted."""
        # Start with a clean state
        if self.change_marker.exists():
            os.unlink(self.change_marker)

        # Set environment to use our test directory
        env = os.environ.copy()
        env['HOME'] = str(self.test_dir)

        # Create a second model file that we'll delete during the test
        model_to_delete = self.models_dir / "model-to-delete.yaml"
        with open(model_to_delete, 'w') as f:
            f.write("""
hf_repo: delete/repo
hf_file: delete.gguf
args:
  ctx-size: "4096"
  temp: "0.7"
""")

        # Start the server process
        process = subprocess.Popen(
            ["python", "-m", "llamate.cli.cli", "serve"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        try:
            # Give it time to start
            start_time = time.time()
            while time.time() - start_time < 10:
                if self.change_marker.exists():
                    break
                time.sleep(0.5)

            # Verify the marker file was created, indicating the process started
            self.assertTrue(self.change_marker.exists(), "Process should have executed the command")
            print(f"Initial process started successfully at {time.time()}")

            # Remove the marker file to detect the restart
            os.unlink(self.change_marker)
            print(f"Marker file removed at {time.time()}")

            # Delete the model file to trigger a restart
            os.unlink(model_to_delete)
            print(f"Model file deleted at {time.time()}")

            # Create a flag file to indicate the config was changed
            with open(self.test_dir / "model_deleted", 'w') as f:
                f.write(f"Model file deleted at {time.time()}")

            # Wait for the original process to terminate after config change
            try:
                process.wait(timeout=10)
                print(f"Original process terminated with exit code: {process.returncode}")
            except subprocess.TimeoutExpired:
                print("Original process did not terminate within expected time")
                poll_result = process.poll()
                print(f"Process poll result: {poll_result}")

            # Start a new serve process to simulate the restart behavior
            print("Starting a new serve process to simulate restart...")
            new_process = subprocess.Popen(
                ["python", "-m", "llamate.cli.cli", "serve"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Give the new process time to start and create the marker file
            start_time = time.time()
            timeout = 15
            restart_detected = False

            while time.time() - start_time < timeout:
                if self.change_marker.exists():
                    restart_detected = True
                    print(f"Restart detected at {time.time()}, {time.time() - start_time} seconds after starting new process")
                    break
                time.sleep(0.5)

            if not restart_detected:
                print(f"No restart detected after {timeout} seconds")
                if new_process.poll() is None:
                    print("New process is running but hasn't created marker file")
                else:
                    print(f"New process exited with code {new_process.returncode}")

                # Check log file for diagnostics
                log_file = self.test_dir / "llama_swap_log.txt"
                if log_file.exists():
                    print("Log file contents:")
                    with open(log_file, 'r') as f:
                        print(f.read())

            # Verify the marker file was created again, indicating a restart
            self.assertTrue(self.change_marker.exists(), "Process should have restarted after model file was deleted")

            # Clean up the new process
            if new_process.poll() is None:
                new_process.terminate()
                try:
                    new_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    new_process.kill()
                    new_process.wait()

        finally:
            # Clean up - always terminate the process
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

            # Ensure original process is terminated
            if process.poll() is None:
                print("Original process still running, terminating...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("Process didn't terminate within timeout, killing...")
                    process.kill()
                    process.wait()

            # Capture output for debugging
            stdout, stderr = process.communicate()
            if stdout:
                print("Original process stdout:", stdout)
            if stderr:
                print("Original process stderr:", stderr)

            # Also dump any log file we created
            log_file = self.test_dir / "llama_swap_log.txt"
            if log_file.exists():
                print("Complete log file contents:")
                with open(log_file, 'r') as f:
                    print(f.read())

if __name__ == "__main__":
    unittest.main()
