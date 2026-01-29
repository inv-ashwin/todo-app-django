document.addEventListener('DOMContentLoaded', () => {
    const list = document.getElementById("task-list");
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    let draggedRow = null;

    // --- Drag and Drop Logic ---
    list.addEventListener("dragstart", e => {
        draggedRow = e.target.closest("tr");
        draggedRow.style.opacity = 0.5;
    });

    list.addEventListener("dragend", () => {
        draggedRow.style.opacity = "";
        updateOrder();
    });

    list.addEventListener("dragover", e => {
        e.preventDefault();
        const targetRow = e.target.closest("tr");
        if (!targetRow || targetRow === draggedRow) return;

        const rect = targetRow.getBoundingClientRect();
        const offset = e.clientY - rect.top;

        if (offset < rect.height / 2) {
            list.insertBefore(draggedRow, targetRow);
        } else {
            list.insertBefore(draggedRow, targetRow.nextSibling);
        }
    });

    function updateOrder() {
        const rows = document.querySelectorAll("#task-list tr");
        const order = Array.from(rows).map((row, index) => ({
            id: row.dataset.id,
            position: index + 1
        }));

        fetch("/update_task_order/", { // Ensure this URL matches your urls.py
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            },
            body: JSON.stringify(order)
        });
    }

    // --- Inline Edit Logic ---
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('task-text')) {
            const cell = e.target.closest('.task-cell');
            cell.querySelector('.display-mode').style.display = 'none';
            cell.querySelector('.edit-mode').style.display = 'flex';
            cell.querySelector('.edit-input').focus();
        }

        if (e.target.classList.contains('cancel-btn')) {
            const cell = e.target.closest('.task-cell');
            cell.querySelector('.display-mode').style.display = 'block';
            cell.querySelector('.edit-mode').style.display = 'none';
        }

        if (e.target.classList.contains('save-btn')) {
            const cell = e.target.closest('.task-cell');
            const taskId = cell.dataset.id;
            const newText = cell.querySelector('.edit-input').value;

            fetch(`/update_task/${taskId}/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": csrfToken
                },
                body: `task=${encodeURIComponent(newText)}`
            })
            .then(response => {
                if (response.ok) {
                    cell.querySelector('.task-text').innerText = newText;
                    cell.querySelector('.display-mode').style.display = 'block';
                    cell.querySelector('.edit-mode').style.display = 'none';
                }
            });
        }
    });
});