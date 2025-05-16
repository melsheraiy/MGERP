/**
 * table_script.js
 * Handles actions within DataTables (edit, delete, confirm order, confirm reception, reorder).
 * Replaces original TableScript.html.
 */

// This function is called by DataTables' `render` for the actions column.
// `row` is the array of data for the current row.
// `currentTableId` is the ID of the table being rendered (e.g., 'NewRequests-table').
function renderActionButtons(row, currentTableId) {
    const entryId = row[0]; // Assuming ID is the first element
    const entryStatus = row[10]; // Assuming Status (display name) is the 11th element
    // const entrySector = row[1]; // Sector name at index 1

    let actionsHtml = '<div class="btn-group btn-group-sm" role="group">'; // Use btn-group-sm for smaller buttons

    let canEdit = false;
    let canDelete = false;
    let canConfirmOrder = false;
    let canConfirmReception = false;
    let canReorder = false;

    // Determine actions based on status and user role (IS_SUPERVISOR from global JS vars)
    // Note: entryStatus is the display name from get_status_display() in Django.
    // Match these with the display names or use the raw status values if passed.
    // For simplicity, using string comparison with display names.
    // In a more robust setup, you might pass the raw status value (e.g., 'New', 'Ordered') in the row data.

    if (entryStatus === (LANG_STRINGS.statusNew || 'New Request')) {
        // Assuming current user can edit/delete their own new requests, or supervisor can.
        // This needs more robust permission checking based on row[13] (username) vs CURRENT_USER_USERNAME
        if (IS_SUPERVISOR || row[13] === CURRENT_USER_USERNAME) {
            canEdit = true;
            canDelete = true;
        }
        if (IS_SUPERVISOR) {
            canConfirmOrder = true;
        }
    } else if (entryStatus === (LANG_STRINGS.statusOrdered || 'Ordered and Waiting for Delivery')) {
        if (IS_SUPERVISOR) { // Supervisor might be able to edit some fields of an ordered item
            canEdit = true; // Or a different type of edit action
        }
        // User who requested OR supervisor can confirm reception
        if (IS_SUPERVISOR || row[13] === CURRENT_USER_USERNAME) {
            canConfirmReception = true;
        }
    } else if (entryStatus === (LANG_STRINGS.statusReceived || 'Received')) {
        // User who requested OR supervisor can reorder
         if (IS_SUPERVISOR || row[13] === CURRENT_USER_USERNAME) {
            canReorder = true;
        }
    }


    if (canEdit) {
        actionsHtml += `<button class="btn btn-outline-primary edit-btn" data-id="${entryId}" title="${LANG_STRINGS.edit || 'تعديل'}"><i class="fas fa-edit"></i></button>`;
    }
    if (canDelete) {
        actionsHtml += `<button class="btn btn-outline-danger delete-btn" data-id="${entryId}" title="${LANG_STRINGS.delete || 'حذف'}"><i class="fas fa-trash-alt"></i></button>`;
    }
    if (canConfirmOrder) {
        actionsHtml += `<button class="btn btn-outline-info confirm-order-btn" data-id="${entryId}" title="${LANG_STRINGS.confirmOrder || 'تأكيد الطلب'}"><i class="fas fa-check-circle"></i></button>`;
    }
    if (canConfirmReception) {
        actionsHtml += `<button class="btn btn-outline-success confirm-reception-btn" data-id="${entryId}" title="${LANG_STRINGS.confirmReception || 'تأكيد الاستلام'}"><i class="fas fa-dolly-flatbed"></i></button>`;
    }
    if (canReorder) { // Reorder button shown for "Received" items
        actionsHtml += `<button class="btn btn-outline-secondary reorder-btn" data-id="${entryId}" title="${LANG_STRINGS.reorder || 'إعادة طلب'}"><i class="fas fa-redo"></i></button>`;
    }

    actionsHtml += '</div>';
    return actionsHtml.includes('<button') ? actionsHtml : '<small class="text-muted">-</small>';
}


$(document).ready(function() {
    // --- Edit Button Action ---
    // Use event delegation for dynamically created buttons in DataTables
    $('table').on('click', '.edit-btn', function() {
        const entryId = $(this).data('id');
        if (!entryId) {
            alert(LANG_STRINGS.errorNoIdForEdit || "Error: No ID found for editing.");
            return;
        }
        // Fetch entry details and populate form (handled in entry_form_script.js)
        $.ajax({
            url: URLS.getEntryDetailsBase + entryId + '/details/',
            method: 'GET',
            dataType: 'json',
            success: function(entryData) {
                if (entryData && entryData.id) {
                    // Switch to the NewEntry section/tab
                    $('#NewEntry-btn').click(); // This will also call clearEntryForm via switchView
                    // Then populate the form
                    if (typeof populateFormForEditOrReorder === 'function') {
                        populateFormForEditOrReorder(entryData, false); // false = not reorder
                    }
                } else {
                    alert(LANG_STRINGS.errorFetchingEditData || 'لم يتم العثور على بيانات الطلب للتحرير أو خطأ: ' + (entryData ? entryData.error : 'لا يوجد بيانات'));
                }
            },
            error: function(xhr) {
                alert((LANG_STRINGS.errorFetchingEditData || "فشل في جلب بيانات الطلب للتحرير: ") + (xhr.responseJSON ? xhr.responseJSON.error : xhr.statusText));
            }
        });
    });

    // --- Delete Button Action ---
    $('table').on('click', '.delete-btn', function() {
        const entryId = $(this).data('id');
        if (!entryId) {
            alert(LANG_STRINGS.errorNoIdForDelete || "Error: No ID found for deletion.");
            return;
        }

        if (confirm(LANG_STRINGS.confirmDeleteRequest || "هل أنت متأكد من رغبتك في حذف هذا الطلب رقم " + entryId + "؟ هذا الإجراء لا يمكن التراجع عنه.")) {
            $.ajax({
                url: URLS.deleteEntryBase + entryId + '/delete/',
                method: 'POST', // Or 'DELETE' if your backend supports it
                headers: { 'X-CSRFToken': CSRF_TOKEN },
                dataType: 'json',
                success: function(response) {
                    alert(response.message); // Show success/failure message from backend
                    if (response.success) {
                        if (typeof refreshCurrentTable === 'function') refreshCurrentTable();
                    }
                },
                error: function(xhr) {
                    alert((LANG_STRINGS.errorDeletingRequest || "فشل حذف الطلب: ") + (xhr.responseJSON ? xhr.responseJSON.message : xhr.statusText));
                }
            });
        }
    });

    // --- Supervisor "Confirm Order" Action ---
    $('table').on('click', '.confirm-order-btn', function() {
        const entryId = $(this).data('id');
        if (!entryId || !IS_SUPERVISOR) { // Double check permission client-side
            alert(LANG_STRINGS.supervisorOnlyConfirmOrder || "فقط المشرف يمكنه تأكيد الطلبات.");
            return;
        }
        $('#confirmOrderError').text('');
        $('#confirmOrderForm')[0].reset(); // Reset the modal form
        $('.form-control').removeClass('is-invalid');


        // Fetch current requested quantity to display in modal
        $.ajax({
            url: URLS.getEntryDetailsBase + entryId + '/details/',
            method: 'GET',
            success: function(entryData) {
                if (entryData && entryData.id) {
                    $('#orderModalEntryId').val(entryData.id);
                    $('#requestedQtyDisplay').val(entryData.requested_qty); // Display original requested qty
                    $('#orderedQtyInput').val(entryData.requested_qty); // Pre-fill ordered with requested
                    $('#confirmOrderModal').modal('show');
                } else {
                     alert((LANG_STRINGS.errorFetchingOrderDetails || 'خطأ: لم يتم العثور على بيانات الطلب. Error: ') + (entryData ? entryData.error : ''));
                }
            },
            error: function() {
                 alert(LANG_STRINGS.errorFetchingOrderDetails || 'فشل جلب بيانات الطلب.');
            }
        });
    });

    $('#submitConfirmOrderBtn').on('click', function() {
        const form = document.getElementById('confirmOrderForm');
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }
        form.classList.remove('was-validated');

        const entryId = $('#orderModalEntryId').val();
        const orderedQty = $('#orderedQtyInput').val();
        const $button = $(this);
        const $submitText = $button.find('.submit-text');
        const $spinner = $button.find('.loading-spinner');

        $('#confirmOrderError').text('');
        $submitText.hide(); $spinner.show(); $button.prop('disabled', true);

        $.ajax({
            url: URLS.confirmOrderBase + entryId + '/confirm-order/',
            method: 'POST',
            data: { ordered_qty: orderedQty, csrfmiddlewaretoken: CSRF_TOKEN },
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    alert(response.message);
                    $('#confirmOrderModal').modal('hide');
                    if (typeof refreshCurrentTable === 'function') refreshCurrentTable();
                } else {
                    const errorMsg = response.errors && response.errors.ordered_qty ? response.errors.ordered_qty[0].message : (response.message || LANG_STRINGS.errorConfirmingOrder);
                    $('#confirmOrderError').text(errorMsg);
                    if(response.errors && response.errors.ordered_qty) $('#orderedQtyInput').addClass('is-invalid');
                }
            },
            error: function(xhr) {
                 $('#confirmOrderError').text((LANG_STRINGS.errorConfirmingOrder || 'فشل تأكيد الطلب: ') + (xhr.responseJSON ? xhr.responseJSON.message : xhr.statusText));
            },
            complete: function() {
                $submitText.show(); $spinner.hide(); $button.prop('disabled', false);
            }
        });
    });


    // --- User "Confirm Reception" Action ---
    $('table').on('click', '.confirm-reception-btn', function() {
        const entryId = $(this).data('id');
        if (!entryId) return;

        $('#confirmReceptionError').text('');
        $('#confirmReceptionForm')[0].reset();
        $('.form-control').removeClass('is-invalid');


        $.ajax({
            url: URLS.getEntryDetailsBase + entryId + '/details/',
            method: 'GET',
            success: function(entryData) {
                if (entryData && entryData.id) {
                    $('#receptionModalEntryId').val(entryData.id);
                    $('#orderedQtyDisplayForReception').val(entryData.ordered_qty); // Display confirmed ordered qty
                    $('#receivedQtyInput').val(entryData.ordered_qty); // Pre-fill received with ordered
                    $('#confirmReceptionModal').modal('show');
                } else {
                    alert((LANG_STRINGS.errorFetchingReceptionDetails || 'خطأ: لم يتم العثور على بيانات الطلب. Error: ') + (entryData ? entryData.error : ''));
                }
            },
            error: function() {
                alert(LANG_STRINGS.errorFetchingReceptionDetails || 'فشل جلب بيانات الطلب.');
            }
        });
    });

    $('#submitConfirmReceptionBtn').on('click', function() {
        const form = document.getElementById('confirmReceptionForm');
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }
        form.classList.remove('was-validated');

        const entryId = $('#receptionModalEntryId').val();
        const receivedQty = $('#receivedQtyInput').val();
        const $button = $(this);
        const $submitText = $button.find('.submit-text');
        const $spinner = $button.find('.loading-spinner');

        $('#confirmReceptionError').text('');
        $submitText.hide(); $spinner.show(); $button.prop('disabled', true);

        $.ajax({
            url: URLS.confirmReceptionBase + entryId + '/confirm-reception/',
            method: 'POST',
            data: { received_qty: receivedQty, csrfmiddlewaretoken: CSRF_TOKEN },
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    alert(response.message);
                    $('#confirmReceptionModal').modal('hide');
                    if (typeof refreshCurrentTable === 'function') refreshCurrentTable();
                } else {
                    const errorMsg = response.errors && response.errors.received_qty ? response.errors.received_qty[0].message : (response.message || LANG_STRINGS.errorConfirmingReception);
                    $('#confirmReceptionError').text(errorMsg);
                     if(response.errors && response.errors.received_qty) $('#receivedQtyInput').addClass('is-invalid');
                }
            },
            error: function(xhr) {
                $('#confirmReceptionError').text((LANG_STRINGS.errorConfirmingReception || 'فشل تأكيد الاستلام: ') + (xhr.responseJSON ? xhr.responseJSON.message : xhr.statusText));
            },
            complete: function() {
                $submitText.show(); $spinner.hide(); $button.prop('disabled', false);
            }
        });
    });

    // --- Reorder Button Action ---
    $('table').on('click', '.reorder-btn', function() {
        const entryId = $(this).data('id');
        if (!entryId) return;

        $.ajax({
            url: URLS.getEntryDetailsBase + entryId + '/details/',
            method: 'GET',
            dataType: 'json',
            success: function(entryData) {
                if (entryData && entryData.id) {
                    $('#NewEntry-btn').click(); // Switch to New Entry form
                    if (typeof populateFormForEditOrReorder === 'function') {
                        populateFormForEditOrReorder(entryData, true); // true = isReorder
                    }
                } else {
                    alert((LANG_STRINGS.errorFetchingReorderData || 'لم يتم العثور على بيانات الطلب لإعادة الطلب أو خطأ: ') + (entryData ? entryData.error : ''));
                }
            },
            error: function(xhr) {
                alert((LANG_STRINGS.errorFetchingReorderData || "فشل في جلب بيانات الطلب لإعادة الطلب: ") + (xhr.responseJSON ? xhr.responseJSON.error : xhr.statusText));
            }
        });
    });
});

// refreshCurrentTableHelper from original Apps Script is replaced by refreshCurrentTable in main_script.js
