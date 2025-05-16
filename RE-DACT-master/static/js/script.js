function toggleOptions() {
    const method = document.getElementById('redactionMethod').value;
    const gradationOptions = document.getElementById('gradationOptions');
    const customOptions = document.getElementById('customOptions');
    const methodField = document.getElementById('methodField');
    
    if (method === 'gradation') {
        gradationOptions.style.display = 'block';
        customOptions.style.display = 'none';
        methodField.value = 'gradation';
    } else {
        gradationOptions.style.display = 'none';
        customOptions.style.display = 'block';
        methodField.value = 'custom';
    }
}

async function previewRedaction() {
    const text = document.getElementById('previewText').value;
    const method = document.getElementById('redactionMethod').value;
    let data = {
        text: text,
        method: method
    };

    if (method === 'gradation') {
        const gradationLevel = document.querySelector('input[name="gradation_level"]:checked').value;
        data.gradation_level = parseInt(gradationLevel);
    } else {
        const selectedTags = Array.from(document.querySelectorAll('input[name="pos_tags"]:checked'))
            .map(cb => cb.value);
        data.pos_tags = selectedTags;
        
        if (selectedTags.length === 0) {
            alert('Please select at least one POS tag for custom redaction.');
            return;
        }
    }

    try {
        const response = await fetch('/process_redaction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        
        if (result.success) {
            document.getElementById('redactedPreview').textContent = result.redacted_text;
            document.getElementById('downloadBtn').style.display = 'inline-block';
        } else {
            alert('Error processing text: ' + result.error);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function downloadRedactedText() {
    const redactedText = document.getElementById('redactedPreview').textContent;
    const blob = new Blob([redactedText], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'redacted_text.txt';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// Initialize the correct view on page load
document.addEventListener('DOMContentLoaded', function() {
    toggleOptions();
});