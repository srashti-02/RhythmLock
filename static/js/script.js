
// ============================================================
// RHYTHMLOCK - TYPING ENROLLMENT
// ============================================================


// ============================================================
// DOM ELEMENTS
// ============================================================

const typingInput = document.getElementById("typingInput");
const startButton = document.getElementById("startButton");
const targetPhraseElement = document.getElementById("targetPhrase");

const statusElement = document.getElementById("status");
const progressElement = document.getElementById("progress");
const sampleProgressElement = document.getElementById("sampleProgress");
const sampleStatusElement = document.getElementById("sampleStatus");

const lastKeyElement = document.getElementById("lastKey");
const dwellTimeElement = document.getElementById("dwellTime");
const flightTimeElement = document.getElementById("flightTime");

const tableBody = document.getElementById("keystrokeTableBody");
const enrollmentCompleteElement =
    document.getElementById("enrollmentComplete");


// ============================================================
// CHECK REQUIRED ELEMENTS
// ============================================================

if (
    !typingInput ||
    !startButton ||
    !targetPhraseElement ||
    !statusElement ||
    !progressElement ||
    !sampleProgressElement ||
    !sampleStatusElement ||
    !lastKeyElement ||
    !dwellTimeElement ||
    !flightTimeElement ||
    !tableBody ||
    !enrollmentCompleteElement
) {
    throw new Error(
        "Rhythmlock enrollment page elements are missing."
    );
}


// ============================================================
// TARGET PHRASE
// ============================================================

const targetPhrase = targetPhraseElement.textContent.trim();

if (!targetPhrase) {
    throw new Error("Target typing phrase is empty.");
}


// ============================================================
// ENROLLMENT SETTINGS
// ============================================================

const TOTAL_SAMPLES = 7;


// ============================================================
// SAMPLE STATE
// ============================================================

let currentSampleNumber = 1;

let currentIndex = 0;

let sampleActive = false;

let sampleData = [];

let keyPressTimes = new Map();

let previousKeyReleaseTime = null;

let baselineRetryMode = false;

let savingInProgress = false;

// True only when a sample save request fails.
let saveRetryRequired = false;


// ============================================================
// IGNORED KEYS
// ============================================================

const ignoredKeys = new Set([
    "Shift",
    "Control",
    "Alt",
    "Meta",
    "CapsLock",
    "Tab",
    "Enter",
    "Escape",
    "ArrowUp",
    "ArrowDown",
    "ArrowLeft",
    "ArrowRight",
    "Home",
    "End",
    "PageUp",
    "PageDown",
    "Delete",
    "Backspace"
]);


// ============================================================
// RESET CURRENT SAMPLE
// ============================================================

function resetCurrentSample() {

    currentIndex = 0;

    sampleActive = false;

    sampleData = [];

    keyPressTimes.clear();

    previousKeyReleaseTime = null;

    typingInput.value = "";

    typingInput.disabled = true;

    progressElement.textContent =
        `0 / ${targetPhrase.length}`;

    lastKeyElement.textContent = "-";

    dwellTimeElement.textContent = "-";

    flightTimeElement.textContent = "-";

    tableBody.innerHTML = "";

    sampleProgressElement.textContent =
        `Sample ${currentSampleNumber} / ${TOTAL_SAMPLES}`;
}


// ============================================================
// START CURRENT SAMPLE
// ============================================================

function startSample() {

    if (
        currentSampleNumber > TOTAL_SAMPLES ||
        savingInProgress ||
        sampleActive
    ) {
        return;
    }

    baselineRetryMode = false;

    // Clear the previous successfully saved sample.
    resetCurrentSample();

    sampleActive = true;

    typingInput.disabled = false;

    typingInput.focus();

    startButton.disabled = true;

    startButton.textContent = "Typing...";

    statusElement.textContent =
        "Type the phrase naturally.";

    sampleStatusElement.textContent =
        `Collecting Sample ${currentSampleNumber}...`;
}


// ============================================================
// ADD KEYSTROKE TO TABLE
// ============================================================

function addKeystrokeToTable(data) {

    const row = document.createElement("tr");

    const numberCell = document.createElement("td");

    const keyCell = document.createElement("td");

    const dwellCell = document.createElement("td");

    const flightCell = document.createElement("td");

    numberCell.textContent = data.index;

    // Display space clearly without changing saved data.
    keyCell.textContent =
        data.key === " " ? "Space" : data.key;

    dwellCell.textContent =
        data.dwellTime.toFixed(2);

    flightCell.textContent =
        data.flightTime === null
            ? "-"
            : data.flightTime.toFixed(2);

    row.appendChild(numberCell);

    row.appendChild(keyCell);

    row.appendChild(dwellCell);

    row.appendChild(flightCell);

    tableBody.appendChild(row);
}


// ============================================================
// SAVE CURRENT SAMPLE TO BACKEND
// ============================================================

async function saveCurrentSample() {

    if (savingInProgress) {
        return;
    }

    // Do not submit incomplete samples.
    if (
        sampleData.length !== targetPhrase.length ||
        currentIndex !== targetPhrase.length
    ) {
        statusElement.textContent =
            "Sample is incomplete. Please complete typing first.";

        return;
    }

    savingInProgress = true;

    statusElement.textContent =
        `Saving Sample ${currentSampleNumber}...`;

    sampleStatusElement.textContent =
        "Saving typing data...";

    startButton.disabled = true;

    // Create a separate payload snapshot.
    const samplePayload = {
        phrase: targetPhrase,
        language: "English",
        keystrokes: sampleData.map((keystroke) => ({
            index: keystroke.index,
            key: keystroke.key,
            dwellTime: keystroke.dwellTime,
            flightTime: keystroke.flightTime
        }))
    };

    console.log(
        `Sending Sample ${currentSampleNumber} to server:`,
        samplePayload
    );

    try {

        const response = await fetch(
            "/api/samples",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(samplePayload)
            }
        );

        const result = await response.json();

        if (!response.ok) {

            throw new Error(
                result.message ||
                "Failed to save sample."
            );
        }

        if (
            !Number.isInteger(result.sample_number) ||
            result.sample_number !== currentSampleNumber
        ) {
            throw new Error(
                "Unexpected sample number received from server."
            );
        }

        console.log(
            "Database response:",
            result
        );

        // Save succeeded. This sample must not be submitted again.
        saveRetryRequired = false;

        statusElement.textContent =
            `Sample ${result.sample_number} saved successfully.`;

        sampleStatusElement.textContent =
            `Sample ${result.sample_number} completed.`;

        currentSampleNumber = result.sample_number;

        // ----------------------------------------------------
        // CHECK IF 7 SAMPLES HAVE BEEN SAVED
        // ----------------------------------------------------

        if (result.sample_number >= TOTAL_SAMPLES) {

            await completeEnrollment();

            return;
        }

        // ----------------------------------------------------
        // MOVE TO NEXT SAMPLE
        // ----------------------------------------------------

        currentSampleNumber = result.sample_number + 1;

        sampleProgressElement.textContent =
            `Sample ${currentSampleNumber} / ${TOTAL_SAMPLES}`;

        statusElement.textContent =
            `Sample ${result.sample_number} saved.`;

        sampleStatusElement.textContent =
            "Take a short moment, then start the next sample.";

        startButton.disabled = false;

        startButton.style.display = "inline-block";

        startButton.textContent = "Start Next Sample";

    } catch (error) {

        console.error("Save error:", error);

        // Keep the captured data for retry.
        saveRetryRequired = true;

        statusElement.textContent =
            "Could not save the sample.";

        sampleStatusElement.textContent =
            error.message || "Please try again.";

        startButton.disabled = false;

        startButton.style.display = "inline-block";

        startButton.textContent = "Retry Saving Sample";

    } finally {

        savingInProgress = false;
    }
}


// ============================================================
// COMPLETE CURRENT SAMPLE
// ============================================================

function completeSample() {

    if (!sampleActive) {
        return;
    }

    sampleActive = false;

    typingInput.disabled = true;

    startButton.disabled = true;

    startButton.textContent = "Saving...";

    statusElement.textContent =
        `Sample ${currentSampleNumber} completed.`;

    sampleStatusElement.textContent =
        "Your typing pattern is being saved.";

    console.log(
        `Completed Sample ${currentSampleNumber}:`,
        sampleData
    );

    // Automatically save sample.
    saveCurrentSample();
}


// ============================================================
// CREATE TYPING BASELINE
// ============================================================

async function createTypingBaseline() {

    if (savingInProgress) {
        return;
    }

    statusElement.textContent =
        "Creating your typing profile...";

    sampleStatusElement.textContent =
        "Please wait while Rhythmlock builds your personal typing baseline.";

    startButton.disabled = true;

    try {

        const response = await fetch(
            "/api/create-baseline",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                }
            }
        );

        const result = await response.json();

        console.log(
            "Baseline response:",
            result
        );

        if (!response.ok) {

            throw new Error(
                result.message ||
                "Failed to create typing profile."
            );
        }

        // ----------------------------------------------------
        // BASELINE SUCCESSFULLY CREATED
        // ----------------------------------------------------

        baselineRetryMode = false;

        startButton.style.display = "none";

        statusElement.textContent =
            "Typing profile created successfully!";

        sampleStatusElement.textContent =
            `${result.sample_count} typing samples were used to create your personal profile.`;

        enrollmentCompleteElement.style.display = "block";

        console.log(
            "Rhythmlock typing profile created successfully."
        );

        // Redirect to dashboard.
        window.location.href = "/dashboard";

    } catch (error) {

        console.error(
            "Baseline creation error:",
            error
        );

        statusElement.textContent =
            "Typing samples were saved, but the typing profile could not be created.";

        sampleStatusElement.textContent =
            error.message || "Please try creating your profile again.";

        baselineRetryMode = true;

        startButton.style.display = "inline-block";

        startButton.disabled = false;

        startButton.textContent =
            "Retry Profile Creation";
    }
}


// ============================================================
// COMPLETE ENROLLMENT
// ============================================================

async function completeEnrollment() {

    sampleActive = false;

    typingInput.disabled = true;

    startButton.disabled = true;

    sampleProgressElement.textContent =
        `Sample ${TOTAL_SAMPLES} / ${TOTAL_SAMPLES}`;

    statusElement.textContent =
        "All typing samples collected. Creating your typing profile...";

    sampleStatusElement.textContent =
        "Please wait while Rhythmlock builds your personal typing profile.";

    console.log(
        "All enrollment samples completed."
    );

    await createTypingBaseline();
}


// ============================================================
// START BUTTON
// ============================================================

startButton.addEventListener("click", function (event) {

    event.preventDefault();

    if (savingInProgress) {
        return;
    }

    // Retry only when the previous save failed.
    if (saveRetryRequired) {
        saveCurrentSample();
        return;
    }

    // Retry baseline creation if required.
    if (baselineRetryMode) {
        createTypingBaseline();
        return;
    }

    // Otherwise, start a fresh sample.
    startSample();
});


// ============================================================
// KEYDOWN EVENT
// ============================================================

typingInput.addEventListener(
    "keydown",
    function (event) {

        if (!sampleActive) {
            return;
        }

        // Ignore control and navigation keys.
        if (ignoredKeys.has(event.key)) {
            return;
        }

        // Ignore repeated keydown.
        if (event.repeat) {
            event.preventDefault();
            return;
        }

        // Expected character.
        const expectedCharacter =
            targetPhrase[currentIndex];

        const pressedCharacter = event.key;

        // ----------------------------------------------------
        // VALIDATE CHARACTER
        // ----------------------------------------------------

        if (pressedCharacter !== expectedCharacter) {

            event.preventDefault();

            sampleActive = false;

            keyPressTimes.clear();

            typingInput.disabled = true;

            startButton.disabled = false;

            startButton.textContent = "Retry Sample";

            statusElement.textContent =
                `Wrong key. Expected "${expectedCharacter}". Please retry Sample ${currentSampleNumber}.`;

            sampleStatusElement.textContent =
                "Sample not saved. Please try again.";

            return;
        }

        // Prevent browser's default input behavior.
        event.preventDefault();

        // Manually display the correctly typed character.
        typingInput.value += expectedCharacter;

        // ----------------------------------------------------
        // CAPTURE PRESS TIME
        // ----------------------------------------------------
        const currentTime = performance.now();

        keyPressTimes.set(
            event.code,
            currentTime
        );

        // Display key.
        let displayKey = event.key;

        if (event.key === " ") {
            displayKey = "Space";
        }

        lastKeyElement.textContent = displayKey;

        // ----------------------------------------------------
        // DISPLAY FLIGHT TIME
        // ----------------------------------------------------

        if (previousKeyReleaseTime !== null) {

            const currentFlightTime =
                currentTime - previousKeyReleaseTime;

            flightTimeElement.textContent =
                currentFlightTime.toFixed(2) + " ms";

        } else {

            flightTimeElement.textContent = "-";
        }
    }
);


// ============================================================
// KEYUP EVENT
// ============================================================

typingInput.addEventListener(
    "keyup",
    function (event) {

        if (!sampleActive) {
            return;
        }

        // Ignore control and navigation keys.
        if (ignoredKeys.has(event.key)) {
            return;
        }

        // Get press time.
        const pressTime =
            keyPressTimes.get(event.code);

        if (pressTime === undefined) {
            return;
        }

        // Release time.
        const releaseTime = performance.now();

        // ----------------------------------------------------
        // CALCULATE DWELL TIME
        // ----------------------------------------------------

        const dwell =
            releaseTime - pressTime;

        // Expected character.
        const expectedCharacter =
            targetPhrase[currentIndex];

        // Preserve actual space character for backend validation.
        const displayKey = expectedCharacter;

        // ----------------------------------------------------
        // CALCULATE FLIGHT TIME
        // ----------------------------------------------------

        let currentFlightTime = null;

        if (previousKeyReleaseTime !== null) {

            currentFlightTime =
                pressTime - previousKeyReleaseTime;
        }

        // ----------------------------------------------------
        // CREATE KEYSTROKE OBJECT
        // ----------------------------------------------------

        const keystrokeData = {

            index: currentIndex + 1,

            key: displayKey,

            dwellTime: dwell,

            flightTime: currentFlightTime
        };

        // Store data.
        sampleData.push(keystrokeData);

        // Update table.
        addKeystrokeToTable(keystrokeData);

        // Update dwell time display.
        dwellTimeElement.textContent =
            dwell.toFixed(2) + " ms";

        previousKeyReleaseTime = releaseTime;

        // Remove stored press timestamp.
        keyPressTimes.delete(event.code);

        // ----------------------------------------------------
        // MOVE TO NEXT CHARACTER
        // ----------------------------------------------------

        currentIndex++;

        progressElement.textContent =
            `${currentIndex} / ${targetPhrase.length}`;

        // ----------------------------------------------------
        // CHECK SAMPLE COMPLETION
        // ----------------------------------------------------

        if (currentIndex === targetPhrase.length) {

            completeSample();
        }
    }
);


// ============================================================
// INITIALIZE ENROLLMENT FROM DATABASE
// ============================================================

async function initializeEnrollment() {

    try {

        statusElement.textContent =
            "Loading your enrollment progress...";

        const response = await fetch(
            "/api/enrollment-status"
        );

        const result = await response.json();

        if (!response.ok) {

            throw new Error(
                result.message ||
                "Could not load enrollment progress."
            );
        }

        // ----------------------------------------------------
        // PROFILE ALREADY EXISTS
        // ----------------------------------------------------

        if (result.profile_created) {

            window.location.href = "/dashboard";

            return;
        }

        // ----------------------------------------------------
        // LOAD SAMPLE COUNT FROM DATABASE
        // ----------------------------------------------------

        currentSampleNumber =
            result.sample_count + 1;

        baselineRetryMode = false;

        saveRetryRequired = false;

        // ----------------------------------------------------
        // SEVEN OR MORE SAMPLES ALREADY SAVED
        // BUT PROFILE DOES NOT EXIST
        // ----------------------------------------------------

        if (result.sample_count >= TOTAL_SAMPLES) {

            sampleProgressElement.textContent =
                `Sample ${TOTAL_SAMPLES} / ${TOTAL_SAMPLES}`;

            typingInput.disabled = true;

            startButton.disabled = true;

            await createTypingBaseline();

            return;
        }

        // ----------------------------------------------------
        // INITIALIZE CURRENT SAMPLE
        // ----------------------------------------------------

        resetCurrentSample();

        sampleProgressElement.textContent =
            `Sample ${currentSampleNumber} / ${TOTAL_SAMPLES}`;

        if (result.sample_count > 0) {

            statusElement.textContent =
                `${result.sample_count} samples already saved. Continue with Sample ${currentSampleNumber}.`;

            sampleStatusElement.textContent =
                `${result.remaining_samples} sample(s) remaining.`;

            startButton.textContent =
                "Continue Enrollment";

        } else {

            statusElement.textContent =
                'Click "Start Sample" to begin.';

            sampleStatusElement.textContent =
                "No sample completed yet.";

            startButton.textContent =
                "Start Sample";
        }

        startButton.disabled = false;

        startButton.style.display = "inline-block";

    } catch (error) {

        console.error(
            "Enrollment initialization error:",
            error
        );

        statusElement.textContent =
            "Could not load your enrollment progress.";

        sampleStatusElement.textContent =
            error.message || "Please refresh the page.";

        startButton.disabled = true;
    }
}


// ============================================================
// INITIALIZE PAGE
// ============================================================

initializeEnrollment();
