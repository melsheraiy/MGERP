/**
 * main_script.js
 * Handles main UI interactions like view switching and initializing DataTables.
 * Replaces parts of the original JavaScript.html
 */

var currentOpenTableId = null; // Tracks which table/section is currently active
var dataTablesInstances = {}; // Store DataTable instances to destroy/recreate

// From original JavaScript.html, adapted for Django URLs
const VIEWS_CONFIG = [
    { buttonId: "NewEntry-btn", sectionId: "NewEntry-section", dataUrl: null, tableId: null, publicName: LANG_STRINGS.newEntry || "إدخال جديد" },
    { buttonId: "NewRequests-btn", sectionId: "NewRequests-section", dataUrl: URLS.getNewRequests, tableId: "NewRequests-table", publicName: LANG_STRINGS.newRequests || "طلبات جديدة" },
    { buttonId: "OrderedWaiting-btn", sectionId: "OrderedWaiting-section", dataUrl: URLS.getOrderedWaiting, tableId: "OrderedWaiting-table", publicName: LANG_STRINGS.orderedWaiting || "طلبات قيد التوصيل" },
    { buttonId: "ReceivedEntries-btn", sectionId: "ReceivedEntries-section", dataUrl: URLS.getReceived, tableId: "ReceivedEntries-table", publicName: LANG_STRINGS.receivedEntries || "الطلبات المستلمة" },
    { buttonId: "TodayEntries-btn", sectionId: "TodayEntries-section", dataUrl: URLS.getTodayEntries, tableId: "TodayEntries-table", publicName: LANG_STRINGS.todayEntries || "إدخالات اليوم" },
    { buttonId: "MonthEntries-btn", sectionId: "MonthEntries-section", dataUrl: URLS.getMonthEntries, tableId: "MonthEntries-table", publicName: LANG_STRINGS.monthEntries || "إدخالات الشهر" }
];

// From original JavaScript.html (DataTables Arabic localization)
const DATA_TABLES_ARABIC = {
    "emptyTable": "لا يوجد بيانات متاحة في الجدول",
    "loadingRecords": "جارٍ التحميل...",
    "processing": "جارٍ المعالجة...",
    "lengthMenu": "أظهر _MENU_ مدخلات",
    "zeroRecords": "لم يُعثر على أية سجلات مطابقة",
    "info": "إظهار _START_ إلى _END_ من أصل _TOTAL_ مدخل",
    "infoEmpty": "يعرض 0 إلى 0 من أصل 0 سجل",
    "infoFiltered": "(مُصفاة من مجموع _MAX_ مُدخل)",
    "search": "ابحث:",
    "paginate": { "first": "الأول", "previous": "السابق", "next": "التالي", "last": "الأخير" },
    "aria": { "sortAscending": ": تفعيل لترتيب العمود تصاعدياً", "sortDescending": ": تفعيل لترتيب العمود تنازلياً" },
    "select": { "rows": { "_": "%d قيمة محددة", "0": "", "1": "1 قيمة محددة" }},
    "buttons": {
        "print": "طباعة", "colvis": "الأعمدة الظاهرة", "copy": "نسخ إلى الحافظة",
        "copyTitle": "نسخ إلى الحافظة",
        "copyKeys": "اضغط على <i>ctrl</i> أو <i>⌘</i> + <i>C</i> لنسخ بيانات الجدول إلى الحافظة الخاصة بك.<br><br>للإلغاء اضغط على الرسالة أو اضغط على esc.",
        "copySuccess": { "_": "تم نسخ %d صفوف بنجاح", "1": "تم نسخ صف واحد بنجاح" },
        "pageLength": { "-1": "اظهار الكل", "_": "إظهار %d أسطر" }
    },
    "decimal": "", "thousands": ","
};

// Column headers order from original Apps Script (used for mapping and consistency)
// The actual headers are set by DataTables based on 'columnsDefinition'
const SERVER_COLUMN_HEADERS_ORDER = [ "م.", "القسم", "الفئة", "الوصف", "ك.مطلوبة", "الوحدة", "ملاحظات", "صورة", "ك.مؤكدة", "ك.مستلمة", "الحالة", "التاريخ", "الوقت", "مستخدم"];


$(document).ready(function() {
    initializeMainUI();

    VIEWS_CONFIG.forEach(view => {
        const button = $('#' + view.buttonId);
        if (button.length) {
            button.on('click', function() {
                switchView(view);
            });
        } else {
            console.warn(`Button with ID ${view.buttonId} not found.`);
        }
    });
});

function initializeMainUI() {
    // This function replaces the onload="initializeUI()" from the original Apps Script's Index.html body tag.
    // It was primarily used to fetch current user data and categories.
    // In Django, user data is passed via context. Categories are loaded by entry_form_script.js.

    // Set up the initial view (e.g., "New Entry" or "New Requests")
    if (VIEWS_CONFIG.length > 0) {
        const initialViewButton = $('#' + VIEWS_CONFIG[0].buttonId); // Default to the first button in config
        if (initialViewButton.length) {
            initialViewButton.click(); // Programmatically click to load the initial view
        } else {
            // Fallback if the first button isn't found, try "NewEntry-btn" explicitly
            $('#NewEntry-btn').click();
        }
    }
     // Call loadCategories from entry_form_script.js to populate the dropdown in the form
    if (typeof loadCategories === 'function') {
        loadCategories(null, null); // Load categories without pre-selecting one
    }
}

function switchView(viewConfig) {
    $('.main-section').addClass('hidden');
    $('#' + viewConfig.sectionId).removeClass('hidden');
    $('.navbutton').removeClass('active');
    $('#' + viewConfig.buttonId).addClass('active');

    const sectionHeader = $('#' + viewConfig.sectionId).find('h3.text-center');
    if (sectionHeader.length) {
        sectionHeader.text(viewConfig.publicName);
    }

    currentOpenTableId = viewConfig.tableId; // Update global tracker

    if (viewConfig.dataUrl && viewConfig.tableId) {
        loadTableData(viewConfig.dataUrl, '#' + viewConfig.tableId, viewConfig.publicName);
    } else if (viewConfig.sectionId === "NewEntry-section") {
        // If switching to the "New Entry" form, clear it.
        if (typeof clearEntryForm === 'function') {
            clearEntryForm(false); // false indicates not a reorder context
        }
    }
}

function loadTableData(dataUrl, tableSelector, tablePublicName) {
    const $table = $(tableSelector);
    const placeholderColspan = SERVER_COLUMN_HEADERS_ORDER.length + 1; // +1 for actions column

    if (dataTablesInstances[tableSelector] && $.fn.DataTable.isDataTable($table)) {
        dataTablesInstances[tableSelector].destroy();
        $table.empty(); // Must empty after destroy
    }

    // Display loading placeholder
    let initialHeaderHtml = '<thead><tr>';
    SERVER_COLUMN_HEADERS_ORDER.forEach(header => initialHeaderHtml += `<th>${header}</th>`);
    initialHeaderHtml += `<th>${LANG_STRINGS.actions || 'إجراءات'}</th></tr></thead>`;
    $table.html(`${initialHeaderHtml}<tbody><tr><td colspan="${placeholderColspan}" class="text-center p-5"><div class="spinner-border spinner-border-sm" role="status"></div> ${LANG_STRINGS.loadingData || 'جاري تحميل البيانات...'}</td></tr></tbody>`);
    $table.attr('dir', 'rtl');

    $.ajax({
        url: dataUrl,
        method: 'GET',
        dataType: 'json',
        success: function(response) {
            if (response && response.data) {
                displayDataInTable(response.data, tableSelector, tablePublicName);
            } else {
                handleTableLoadError($table, placeholderColspan, LANG_STRINGS.noDataAvailable || "No data received from server.");
            }
        },
        error: function(xhr, status, error) {
            console.error("loadTableData AJAX Error:", status, error, xhr.responseText);
            const errorMsg = xhr.responseJSON && xhr.responseJSON.error ? xhr.responseJSON.error : (LANG_STRINGS.errorLoadingData || "Failed to load data.");
            handleTableLoadError($table, placeholderColspan, errorMsg);
        }
    });
}

function handleTableLoadError($table, colspan, errorMessage) {
    if (dataTablesInstances[$table.selector] && $.fn.DataTable.isDataTable($table)) {
         dataTablesInstances[$table.selector].destroy();
    }
    $table.empty();
    let headerHtml = '<thead><tr>';
    SERVER_COLUMN_HEADERS_ORDER.forEach(header => headerHtml += `<th>${header}</th>`);
    headerHtml += `<th>${LANG_STRINGS.actions || 'إجراءات'}</th></tr></thead>`;
    $table.html(`${headerHtml}<tbody><tr><td colspan="${colspan}" class="text-center p-5 text-danger">${errorMessage}</td></tr></tbody>`);
}


function displayDataInTable(tableDataRows, tableIdSelector, tablePublicName) {
    const $table = $(tableIdSelector);
    if (dataTablesInstances[tableIdSelector] && $.fn.DataTable.isDataTable($table)) {
        dataTablesInstances[tableIdSelector].destroy();
    }
    $table.empty(); // Clear previous content including placeholder

    if (!tableDataRows || tableDataRows.length === 0) {
        let headersForEmpty = SERVER_COLUMN_HEADERS_ORDER;
        let colspan = headersForEmpty.length + 1;
        let headerHtml = '<thead><tr>';
        headersForEmpty.forEach(header => headerHtml += `<th>${header}</th>`);
        headerHtml += `<th>${LANG_STRINGS.actions || 'إجراءات'}</th></tr></thead>`;
        $table.html(`${headerHtml}<tbody><tr><td colspan="${colspan}" class="text-center p-5">${LANG_STRINGS.noDataToDisplay || 'لا توجد بيانات لعرضها حالياً.'}</td></tr></tbody>`);
        $table.attr('dir', 'rtl');
        return;
    }

    // Column definitions, mapping to the order from _format_entry_for_datatables in views.py
    // Indices: 0:id, 1:sector, 2:category, 3:description, 4:req_qty, 5:unit, 6:notes, 7:photo_obj,
    // 8:ord_qty, 9:rec_qty, 10:status, 11:date, 12:time, 13:username
    let columnsDefinition = [
        { title: SERVER_COLUMN_HEADERS_ORDER[0], data: 0, className: "text-center" }, // ID (م.)
        { title: SERVER_COLUMN_HEADERS_ORDER[1], data: 1 }, // Sector (القسم)
        { title: SERVER_COLUMN_HEADERS_ORDER[2], data: 2 }, // Category (الفئة)
        { title: SERVER_COLUMN_HEADERS_ORDER[3], data: 3, className: "description-column" }, // Description (الوصف)
        { title: SERVER_COLUMN_HEADERS_ORDER[4], data: 4, className: "text-center" }, // Requested Qty (ك.مطلوبة)
        { title: SERVER_COLUMN_HEADERS_ORDER[5], data: 5, className: "text-center" }, // Unit (الوحدة)
        { title: SERVER_COLUMN_HEADERS_ORDER[6], data: 6, className: "notes-column" }, // Notes (ملاحظات)
        { // Photo (صورة)
            title: SERVER_COLUMN_HEADERS_ORDER[7], data: 7, orderable: false, className: "text-center photo-column",
            render: function(photoData, type, row) {
                if (photoData && photoData.url) {
                    const viewUrl = photoData.url;
                    const thumbnailUrl = photoData.thumbnail || viewUrl; // Fallback to full URL if no thumbnail
                    return `<a href="${viewUrl}" target="_blank" title="${LANG_STRINGS.viewFullImage || 'عرض الصورة بحجم كامل'}">
                                <img src="${thumbnailUrl}" alt="${LANG_STRINGS.photoAlt || 'صورة'}"
                                     style="max-height:30px; max-width:40px; border:1px solid #eee; border-radius:3px; object-fit: cover;"
                                     onerror="this.style.display='none'; var parent = this.parentElement; if(parent){ var textNode = document.createElement('small'); textNode.className='text-muted'; textNode.textContent='(×)'; if(!parent.querySelector('small.text-muted')) parent.appendChild(textNode); }" />
                            </a>`;
                }
                return '<small class="text-muted">-</small>';
            }
        },
        { title: SERVER_COLUMN_HEADERS_ORDER[8], data: 8, className: "text-center" }, // Ordered Qty (ك.مؤكدة)
        { title: SERVER_COLUMN_HEADERS_ORDER[9], data: 9, className: "text-center" }, // Received Qty (ك.مستلمة)
        { title: SERVER_COLUMN_HEADERS_ORDER[10], data: 10, className: "text-center" }, // Status (الحالة)
        { title: SERVER_COLUMN_HEADERS_ORDER[11], data: 11, className: "text-center" }, // Date (التاريخ)
        { title: SERVER_COLUMN_HEADERS_ORDER[12], data: 12, className: "text-center" }, // Time (الوقت)
        { title: SERVER_COLUMN_HEADERS_ORDER[13], data: 13, className: "text-center" }  // User (مستخدم)
    ];

    // Dynamically hide columns based on current table view (similar to original Apps Script)
    let columnsToHideIndices = []; // Store indices of columns to hide
    if (currentOpenTableId === 'NewRequests-table') { // Hide: ordered_qty[8], received_qty[9], status[10], time[12]
        columnsToHideIndices = [8, 9, 10, 12];
    } else if (currentOpenTableId === 'OrderedWaiting-table') { // Hide: received_qty[9], status[10], time[12]
        columnsToHideIndices = [9, 10, 12];
    } else if (currentOpenTableId === 'ReceivedEntries-table') { // Hide: status[10], time[12]
        columnsToHideIndices = [10, 12];
    }
    // Apply visibility
    columnsToHideIndices.forEach(idx => {
        if (columnsDefinition[idx]) columnsDefinition[idx].visible = false;
    });

    // Supervisor specific column visibility (e.g., sector might be always visible for supervisor)
    // if (!IS_SUPERVISOR) {
    //    if(columnsDefinition[1]) columnsDefinition[1].visible = false; // Hide Sector for non-supervisors
    //    if(columnsDefinition[2]) columnsDefinition[2].visible = false; // Hide Category for non-supervisors (if it was sector specific)
    // }


    // Actions Column (dynamically built in table_script.js)
    columnsDefinition.push({
        title: LANG_STRINGS.actions || "إجراءات", data: null, // No specific data source, rendered based on row
        orderable: false, searchable: false, className: "text-center actions-column",
        render: function(data, type, row) {
            // Delegate rendering to a function in table_script.js
            if (typeof renderActionButtons === 'function') {
                return renderActionButtons(row, currentOpenTableId);
            }
            return '-';
        }
    });

    const dtOptions = {
        data: tableDataRows,
        columns: columnsDefinition,
        destroy: true,
        responsive: false, // Set to true for better mobile, but original was false
        autoWidth: false,
        pageLength: 10,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, LANG_STRINGS.all || "الكل"]],
        ordering: true,
        order: [[0, "desc"]], // Default order by ID (index 0) descending
        language: DATA_TABLES_ARABIC,
        createdRow: function(row, data, dataIndex) {
            // Add tooltips for description/notes if visible
            const descriptionText = data[3]; // Description at index 3
            const notesText = data[6];       // Notes at index 6

            const visibleDescColIndex = columnsDefinition.findIndex(col => col.data === 3 && col.visible !== false);
            const visibleNotesColIndex = columnsDefinition.findIndex(col => col.data === 6 && col.visible !== false);

            if (descriptionText && visibleDescColIndex !== -1) {
                $(row).find('td').eq(visibleDescColIndex).attr('title', descriptionText);
            }
            if (notesText && visibleNotesColIndex !== -1) {
                $(row).find('td').eq(visibleNotesColIndex).attr('title', notesText);
            }
        },
        // DOM and Buttons (Supervisor gets print, others don't)
        dom: IS_SUPERVISOR ?
            "<'row'<'col-sm-12 col-md-3'l><'col-sm-12 col-md-6 text-center'B><'col-sm-12 col-md-3'f>>" + "<'row'<'col-sm-12'tr>>" + "<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>" :
            "<'row'<'col-sm-12 col-md-6'l><'col-sm-12 col-md-6'f>>" + "<'row'<'col-sm-12'tr>>" + "<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
        buttons: IS_SUPERVISOR ? [
            {
                extend: 'print',
                text: '<i class="fas fa-print mr-1"></i> ' + (LANG_STRINGS.print || 'طباعة'),
                className: 'btn btn-sm btn-secondary dt-button',
                title: function() { return tablePublicName || (LANG_STRINGS.sparePartsReport || 'تقرير قطع الغيار'); },
                exportOptions: {
                    columns: ':visible:not(.actions-column):not(.photo-column)' // Exclude actions and photo from print
                },
                customize: function (win) {
                    $(win.document.body).css('font-size', '10pt').css('text-align', 'right');
                    $(win.document.head).append('<style>body { direction: rtl; margin: 20px !important; } table { width: 100% !important; } table td, table th { border: 1px solid #ccc !important; padding: 4px !important; text-align: right !important; } img { display: none !important; } </style>');
                    const clientDate = new Date().toLocaleString('ar-EG', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
                    $(win.document.body).prepend(
                        `<div style="text-align:center; font-size:14pt; font-weight:bold; margin-bottom:10px;">${tablePublicName || (LANG_STRINGS.sparePartsReport || 'تقرير قطع الغيار')}</div>
                         <div style="text-align:left; font-size:9pt; margin-bottom:20px;">${LANG_STRINGS.printDate || 'تاريخ الطباعة'}: ${clientDate}</div>`
                    );
                    $(win.document.body).find('h1').remove();
                    $(win.document.body).find('table').addClass('compact table-bordered');
                },
                autoPrint: false
            }
        ] : []
    };

    dataTablesInstances[tableIdSelector] = $table.DataTable(dtOptions);
    $table.attr('dir', 'rtl'); // Ensure RTL direction
}

// Helper function to refresh the currently open table
function refreshCurrentTable() {
    const view = VIEWS_CONFIG.find(v => v.tableId === currentOpenTableId);
    if (view && view.dataUrl && view.tableId) {
        loadTableData(view.dataUrl, '#' + view.tableId, view.publicName);
    } else if (currentOpenTableId === null && $('#NewEntry-btn').hasClass('active')) {
        // If on New Entry form, no table to refresh, but maybe clear form message
        $('#formMessage').html('');
    } else {
        console.warn("Could not refresh table, view config not found for tableId:", currentOpenTableId);
        // Fallback: Try to click the active button again, or a default button
        const $activeButton = $('.navbutton.active');
        if ($activeButton.length) {
            $activeButton.click();
        } else if ($('#NewRequests-btn').length) {
            $('#NewRequests-btn').click();
        }
    }
}
