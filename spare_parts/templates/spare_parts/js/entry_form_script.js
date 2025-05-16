/**
 * entry_form_script.js
 * Handles the logic for the spare part entry form, including photo previews,
 * category loading, form submission, and populating for edit/reorder.
 * Replaces parts of original EntryFormScript.html and some logic from JavaScript.html (initializeUI).
 */

let selectedPhotoFile = null; // Stores { name, type, base64Data } for new photo
let shouldRemoveExistingPhoto = false; // Flag for removing photo during edit
let clientSideCachedCategories = null; // Cache for categories dropdown

$(document).ready(function() {
    // Event listener for photo input change
    $('#sparePartPhoto').on('change', function(event) {
        handlePhotoInputChange(event, this);
    });

    // Event listener for "Remove Current Image" button (if it exists)
    // This button is dynamically added/shown, so delegate event
    $('#sparePartForm').on('click', '#removeCurrentImageBtn', function() {
        handleRemoveCurrentImage();
    });

    // Event listener for form submission button
    $('#submitSparePartFormBtn').on('click', function() {
        submitSparePartForm();
    });

    // Event listener for "Clear & New Entry" button
    $('#clearEntryFormBtn').on('click', function() {
        clearEntryFormAndSwitch();
    });

    // Supervisor status change handling (if supervisor form elements are present)
    $('#sparePartForm').on('change', '#id_status', function() { // Assuming id_status is the ID for the supervisor's status select
        const statusVal = $(this).val();
        const $receivedQtyGroup = $('#receivedQtyGroup'); // The div containing received_qty_form_input
        const $receivedQtyInput = $('#id_received_qty_form_input'); // Assuming this ID

        if (statusVal === 'Received') { // 'Received' is the value from SparePartRequest.STATUS_RECEIVED
            $receivedQtyGroup.show();
            $receivedQtyInput.prop('required', true);
        } else {
            $receivedQtyGroup.hide();
            $receivedQtyInput.prop('required', false).val(''); // Clear and make not required
        }
    });
});


function handlePhotoInputChange(event, inputElement) {
    const file = event.target.files[0];
    const $newPhotoPreviewContainer = $('#newPhotoPreviewContainer');
    const $newPhotoPreview = $('#newPhotoPreview');

    if (file) {
        if (file.size > 5 * 1024 * 1024) { // 5MB limit
            alert(LANG_STRINGS.fileTooLarge || "حجم الملف كبير جداً. الحد الأقصى 5 ميجا بايت.");
            $(inputElement).val(''); // Clear the input
            selectedPhotoFile = null;
            $newPhotoPreviewContainer.hide();
            $newPhotoPreview.attr('src', '#').attr('alt', '');
            return;
        }
        selectedPhotoFile = { name: file.name, type: file.type, base64Data: null };
        const reader = new FileReader();
        reader.onload = function(e) {
            selectedPhotoFile.base64Data = e.target.result; // Full base64 string
            $newPhotoPreview.attr('src', e.target.result).attr('alt', LANG_STRINGS.newPhotoPreviewAlt || 'معاينة الصورة الجديدة');
            $newPhotoPreviewContainer.show();
        };
        reader.onerror = function() {
            alert(LANG_STRINGS.errorReadingFile || "حدث خطأ أثناء قراءة الملف.");
            selectedPhotoFile = null;
        };
        reader.readAsDataURL(file);
    } else {
        selectedPhotoFile = null;
        $newPhotoPreviewContainer.hide();
        $newPhotoPreview.attr('src', '#').attr('alt', '');
    }
}

function handleRemoveCurrentImage() {
    shouldRemoveExistingPhoto = true;
    $('#currentPhotoPreviewContainer').hide();
    $('#currentPhotoDriveId').val(''); // Clear hidden field storing current photo ID/URL
    // Show a message that current photo will be removed
    $('#formMessage').html(`<div class="alert alert-warning small mt-2">${LANG_STRINGS.photoWillBeRemoved || 'سيتم إزالة الصورة الحالية عند الحفظ.'}</div>`);
    // Ensure the "Remove photo" checkbox (if using Django forms `remove_photo` field) is checked
    $('#id_remove_photo').prop('checked', true); // Assuming 'id_remove_photo' is the ID of the checkbox
}


function _populateCategoryDropdown(categoriesToPopulate, categoryToSelectId, callback) {
    const $categorySelect = $('#id_category'); // Assuming 'id_category' is the ID of the select input
    $categorySelect.empty().append(`<option value="">${LANG_STRINGS.selectCategory || 'اختر الفئة...'}</option>`);

    if (categoriesToPopulate && categoriesToPopulate.length > 0) {
        categoriesToPopulate.forEach(function(cat) {
            $categorySelect.append($('<option></option>').attr('value', cat.id).text(cat.name));
        });
    } else {
        // Handle no categories found (e.g., for supervisor if none exist, or for user if their sector has none)
        // This message might depend on whether IS_SUPERVISOR or IS_MELSHERAIY
        const noCategoriesMsg = (IS_SUPERVISOR || IS_MELSHERAIY) ?
                                (LANG_STRINGS.noCategoriesDefined || 'لا توجد فئات معرفة في النظام.') :
                                (LANG_STRINGS.noCategoriesForSector || 'لا توجد فئات لهذا القسم.');
        $categorySelect.append(`<option value="" disabled>${noCategoriesMsg}</option>`);
    }

    if (categoryToSelectId) {
        $categorySelect.val(categoryToSelectId);
    }
    if (callback) callback();
}

function loadCategories(categoryToSelectId, callback) {
    // In Django, currentUserData is available via template variables like CURRENT_USER_USERNAME, IS_SUPERVISOR etc.
    // No need to fetch it separately here unless more details are needed that aren't passed.

    if (clientSideCachedCategories !== null) {
        // console.log("Using cached categories");
        _populateCategoryDropdown(clientSideCachedCategories, categoryToSelectId, callback);
    } else {
        // console.log("Fetching categories from server");
        $('#id_category').empty().append(`<option value="">${LANG_STRINGS.loadingCategories || 'جاري تحميل الفئات...'}</option>`);

        $.ajax({
            url: URLS.listCategories, // URL from global URLS object
            method: 'GET',
            dataType: 'json',
            success: function(categoriesFromServer) {
                clientSideCachedCategories = categoriesFromServer || [];
                _populateCategoryDropdown(clientSideCachedCategories, categoryToSelectId, callback);
            },
            error: function(xhr, status, error) {
                console.error("Failed to load categories from server:", error);
                clientSideCachedCategories = []; // Set to empty on error
                _populateCategoryDropdown([], categoryToSelectId, callback); // Populate with empty
                // Optionally show an error message to the user
            }
        });
    }
}

function populateFormForEditOrReorder(entryData, isReorder = false) {
    clearEntryForm(isReorder); // Clear form first, isReorder helps set title correctly

    $('#entryFormTitle').text(isReorder ? (LANG_STRINGS.reorderItemTitle || 'إعادة طلب قطعة غيار') : (LANG_STRINGS.editItemTitle || 'تعديل طلب قطعة غيار'));
    $('#entryId').val(isReorder ? '' : entryData.id); // No ID for reorder (it's a new entry)

    // Load categories and then populate other fields in the callback
    loadCategories(entryData.category_id, function() {
        // This callback runs AFTER categories are loaded and entryData.category_id is selected (if found)
        $('#id_description').val(entryData.description);
        $('#id_requested_qty').val(entryData.requested_qty);
        $('#id_unit').val(entryData.unit);
        $('#id_notes').val(entryData.notes);

        const $currentPhotoPreviewContainer = $('#currentPhotoPreviewContainer');
        const $currentPhotoPreview = $('#currentPhotoPreview');
        const $currentPhotoLink = $('#currentPhotoLink');
        const $removeCurrentImageBtnContainer = $currentPhotoPreviewContainer.find('.form-check'); // Assuming checkbox is for remove

        if (entryData.photo_url && !isReorder) {
            $('#currentPhotoDriveId').val(entryData.photo_url); // Store photo URL
            $currentPhotoLink.attr('href', entryData.photo_url);
            $currentPhotoPreview.attr('src', entryData.photo_url)
                                 .attr('alt', LANG_STRINGS.currentPhotoAlt || 'الصورة الحالية')
                                 .off('error') // Remove previous error handlers
                                 .on('error', function() {
                                     $(this).hide();
                                     $currentPhotoLink.hide();
                                     $currentPhotoPreviewContainer.find('label.float-right').after(`<div class="text-muted small mt-1">${LANG_STRINGS.previewError || 'تعذر عرض الصورة المصغرة.'} <a href="${entryData.photo_url}" target="_blank">${LANG_STRINGS.openImageDirectly || 'افتح الصورة مباشرة'}</a>.</div>`);
                                     if ($removeCurrentImageBtnContainer.length) $removeCurrentImageBtnContainer.show();
                                 });
            $currentPhotoPreviewContainer.show();
            if ($removeCurrentImageBtnContainer.length) $removeCurrentImageBtnContainer.show();
            $('#id_remove_photo').prop('checked', false); // Ensure "remove photo" is unchecked initially
        } else {
            $currentPhotoPreviewContainer.hide();
            if ($removeCurrentImageBtnContainer.length) $removeCurrentImageBtnContainer.hide();
        }

        // Supervisor-specific fields handling (status, received_qty)
        const $supervisorStatusSection = $('#supervisorStatusSection');
        if (!isReorder && IS_SUPERVISOR && entryData.status !== 'New') { // 'New' is the value for New status
            $supervisorStatusSection.show();
            $('#id_status').val(entryData.status).trigger('change'); // Set status and trigger change to show/hide received_qty
            if (entryData.status === 'Received') { // 'Received' is the value for Received status
                $('#id_received_qty_form_input').val(entryData.received_qty || entryData.requested_qty);
            }
        } else {
            $supervisorStatusSection.hide();
            $('#id_status').val('New'); // Default for new/non-supervisor edit
            $('#id_received_qty_form_input').val('');
        }
        // Store current status for non-supervisor edits (if form doesn't have status field for them)
        $('#currentStatusHidden').val(entryData.status);


        const messageType = isReorder ? 'info' : 'info';
        const messageText = isReorder ?
            (LANG_STRINGS.reorderFormReady || 'نموذج جاهز لإعادة الطلب. يرجى مراجعة الكمية والتفاصيل الأخرى.') :
            (LANG_STRINGS.editingRequest || 'أنت تقوم بتعديل الطلب رقم: ') + entryData.id;
        $('#formMessage').html(`<div class="alert alert-${messageType} small mt-2">${messageText}</div>`);

        if (isReorder) {
            $('#id_requested_qty').focus();
        }
    });
}


function clearEntryForm(isReorderContext = false) {
    $('#sparePartForm')[0].reset(); // Resets native form elements
    $('.form-control').removeClass('is-invalid'); // Clear validation states
    $('.invalid-feedback').text(''); // Clear validation messages
    $('#formMessage').html('');

    $('#entryId').val('');
    $('#currentStatusHidden').val('');
    $('#currentPhotoDriveId').val('');

    selectedPhotoFile = null;
    shouldRemoveExistingPhoto = false;
    $('#sparePartPhoto').val(''); // Clear file input
    $('#newPhotoPreviewContainer').hide();
    $('#newPhotoPreview').attr('src', '#').attr('alt', '');
    $('#currentPhotoPreviewContainer').hide();
    $('#id_remove_photo').prop('checked', false);


    // Hide supervisor-specific sections by default on clear
    $('#supervisorStatusSection').hide();
    $('#id_status').val('New'); // Default status
    $('#receivedQtyGroup').hide();
    $('#id_received_qty_form_input').prop('required', false).val('');


    if (!isReorderContext) {
        $('#entryFormTitle').text(LANG_STRINGS.newEntryFormTitle || 'نموذج طلب قطعة غيار جديدة');
    }

    // Reload categories, ensuring the first "Select Category..." option is chosen
    loadCategories(null, null);
}

function clearEntryFormAndSwitch() {
    clearEntryForm(false);
    // Switch view back to "New Entry" tab if not already there (handled by main_script.js button click)
    // This function is primarily for the "Clear & New Entry" button within the form section.
    // It effectively just clears the form. The view itself is already "NewEntry-section".
    $('#id_category').focus(); // Focus on the first field
}


function submitSparePartForm() {
    const form = document.getElementById('sparePartForm');
    if (!form.checkValidity()) {
        form.classList.add('was-validated'); // Show Bootstrap validation styles
        $('#formMessage').html(`<div class="alert alert-danger small mt-2">${LANG_STRINGS.fillRequiredFields || 'يرجى ملء جميع الحقول المطلوبة ذات العلامة (*).'}</div>`);
        // Find first invalid field and focus it
        $(form).find(':invalid').first().focus();
        return;
    }
    form.classList.remove('was-validated'); // Reset if valid so far

    const $submitButton = $('#submitSparePartFormBtn');
    const $submitText = $submitButton.find('.submit-text');
    const $loadingSpinner = $submitButton.find('.loading-spinner');

    $submitText.hide();
    $loadingSpinner.show();
    $submitButton.prop('disabled', true);
    $('#formMessage').html(`<div class="alert alert-info small mt-2">${LANG_STRINGS.savingInProgress || 'جاري الحفظ...'}</div>`);

    const formData = new FormData(form); // Use FormData for file uploads

    // Append base64 photo data if a new photo was selected (server-side needs to handle this)
    // Django's request.FILES should handle the 'photo' field directly if it's a file input.
    // If you were sending base64, you'd append it:
    // if (selectedPhotoFile && selectedPhotoFile.base64Data) {
    //     formData.append('photo_base64', selectedPhotoFile.base64Data);
    //     formData.append('photo_filename', selectedPhotoFile.name);
    //     formData.append('photo_filetype', selectedPhotoFile.type);
    // }
    // formData.append('remove_existing_photo', shouldRemoveExistingPhoto); // If using a separate flag

    // If not a supervisor form, status is not directly on the form, get from hidden or default
    if (!IS_SUPERVISOR || !$('#supervisorStatusSection').is(':visible')) {
        const currentStatus = $('#currentStatusHidden').val();
        formData.set('status', currentStatus || 'New'); // Set status if not part of the visible form
        // Remove supervisor-specific fields if they were somehow included by FormData from hidden sections
        formData.delete('received_qty_form_input'); // Django form name for this field
    } else {
        // Ensure status is correctly set from the supervisor's select field
        formData.set('status', $('#id_status').val());
        if (formData.get('status') !== 'Received') {
             formData.delete('received_qty_form_input'); // Remove if status is not 'Received'
        }
    }


    $.ajax({
        url: URLS.saveEntry,
        method: 'POST',
        data: formData,
        processData: false, // Important for FormData
        contentType: false, // Important for FormData
        headers: { 'X-CSRFToken': CSRF_TOKEN },
        success: function(response) {
            if (response.success) {
                $('#formMessage').html(`<div class="alert alert-success small mt-2">${response.message}</div>`);
                const originalEntryId = formData.get('id'); // Get ID before clearing

                clearEntryForm(false); // Clear form for next entry

                // Refresh the table that was open or default to "New Requests"
                // This logic is now in main_script.js's refreshCurrentTable()
                if (typeof refreshCurrentTable === 'function') {
                    refreshCurrentTable(); // This will try to reload the currently active table
                }
                // Optionally, switch to a specific view after successful save
                // For example, switch to "New Requests" view:
                // const newRequestsView = VIEWS_CONFIG.find(v => v.buttonId === 'NewRequests-btn');
                // if (newRequestsView) {
                //     $('#' + newRequestsView.buttonId).click();
                // }

            } else {
                let errorMessages = '';
                if (response.errors) {
                    for (const field in response.errors) {
                        response.errors[field].forEach(err => {
                            errorMessages += `<div>${field}: ${err.message}</div>`;
                            // Highlight the field with error
                            $('#id_' + field).addClass('is-invalid').siblings('.invalid-feedback').text(err.message);
                        });
                    }
                }
                $('#formMessage').html(`<div class="alert alert-danger small mt-2">${response.message || LANG_STRINGS.errorSavingData} ${errorMessages}</div>`);
            }
        },
        error: function(xhr, status, error) {
            console.error("Save entry error:", xhr.responseText);
            const errorMsg = xhr.responseJSON && xhr.responseJSON.message ? xhr.responseJSON.message : (LANG_STRINGS.serverError || "فشل في الاتصال بالخادم.");
            $('#formMessage').html(`<div class="alert alert-danger small mt-2">${errorMsg}</div>`);
        },
        complete: function() {
            $submitText.show();
            $loadingSpinner.hide();
            $submitButton.prop('disabled', false);
        }
    });
}
