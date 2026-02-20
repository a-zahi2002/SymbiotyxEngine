"""
sequence_buffer.py
------------------
A simple in-memory buffer for storing gesture frames temporarily.

This module is part of the SymbiotixEngine capture pipeline.
It does NOT contain any ML logic — it is purely a data container
that holds frame dictionaries until they are saved or processed.

Compatible with Python 3.10+ and Windows.
"""


class SequenceBuffer:
    """
    A temporary in-memory buffer that stores gesture frames as dictionaries.

    Each "frame" is a snapshot of gesture data captured at a single moment
    (e.g., hand landmark coordinates, a timestamp, etc.).

    Frames are stored in the order they were added, forming a sequence
    that can later be saved or passed to a processing pipeline.

    Example:
        buffer = SequenceBuffer()
        buffer.add_frame({"landmarks": [...], "timestamp": 1234567890})
        print(len(buffer))  # 1
    """

    def __init__(self) -> None:
        """
        Initialize the SequenceBuffer with an empty list.

        The internal list `_frames` holds all frame dictionaries
        added during a capture session.
        """
        # Internal list to hold all captured frames
        self._frames: list[dict] = []

    def add_frame(self, frame_data: dict) -> None:
        """
        Add a single frame of gesture data to the buffer.

        A frame is expected to be a dictionary containing whatever
        data was captured in one moment (e.g., landmarks, timestamp).

        Args:
            frame_data (dict): A dictionary representing one captured frame.

        Example:
            buffer.add_frame({"landmarks": [0.1, 0.2, 0.3], "timestamp": 1000})
        """
        # Append the new frame dictionary to our internal list
        self._frames.append(frame_data)

    def get_sequence(self) -> list[dict]:
        """
        Return the full list of stored frames.

        The frames are returned in the order they were added,
        from oldest (index 0) to newest (last index).

        Returns:
            list[dict]: A list of all frame dictionaries in the buffer.

        Example:
            sequence = buffer.get_sequence()
            print(sequence)  # [{"landmarks": [...], "timestamp": ...}, ...]
        """
        # Return a copy so the caller can't accidentally modify our internal list
        return list(self._frames)

    def clear(self) -> None:
        """
        Remove all frames from the buffer.

        Use this to reset the buffer between recording sessions,
        so old data doesn't mix with new data.

        Example:
            buffer.clear()
            print(len(buffer))  # 0
        """
        # Reset the internal list to empty
        self._frames = []

    def __len__(self) -> int:
        """
        Return the number of frames currently stored in the buffer.

        This allows you to use the built-in `len()` function directly
        on a SequenceBuffer instance.

        Returns:
            int: The number of frames stored.

        Example:
            print(len(buffer))  # e.g., 42
        """
        return len(self._frames)


# ---------------------------------------------------------------------------
# Example usage — runs only when this script is executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== SequenceBuffer Demo ===\n")

    # Step 1: Create a new buffer
    buffer = SequenceBuffer()
    print(f"Buffer created. Frames stored: {len(buffer)}")  # Expected: 0

    # Step 2: Add two mock frames (simulating captured gesture data)
    mock_frame_1 = {
        "timestamp": 1000,
        "landmarks": [0.1, 0.2, 0.3, 0.4, 0.5],
        "label": "open_hand",
    }
    mock_frame_2 = {
        "timestamp": 1033,
        "landmarks": [0.6, 0.7, 0.8, 0.9, 1.0],
        "label": "fist",
    }

    buffer.add_frame(mock_frame_1)
    buffer.add_frame(mock_frame_2)
    print(f"Added 2 frames. Frames stored: {len(buffer)}")  # Expected: 2

    # Step 3: Print the stored sequence
    print("\nStored sequence:")
    for i, frame in enumerate(buffer.get_sequence()):
        print(f"  Frame {i}: {frame}")

    # Step 4: Clear the buffer
    buffer.clear()
    print(f"\nBuffer cleared. Frames stored: {len(buffer)}")  # Expected: 0
