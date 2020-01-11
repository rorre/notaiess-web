var count = 0
const mode_mapping = {
    std: 1,
    taiko: 2,
    catch: 4,
    mania: 8
}

const status_mapping = {
    bubble: 1,
    qualify: 2,
    disqualify: 4,
    pop: 8,
    ranked: 16,
    loved: 32
}

var owned_hooks = {}

function add_data(v) {
    owned_hooks[v.id] = v
    count++
    $("#table-content").append(`<tr id="table-${v.id}">
        <th scope="col">${count}</th>
        <th scope="col">${v.url}</th>
        <th scope="col">${getEnumValue(v.mode, mode_mapping)}</th>
        <th scope="col">${getEnumValue(v.push_status, status_mapping)}</th>
        <th scope="col">${v.status}</th>
        <th scope="col">
            <a href="/${v.id}" id="btn${count}-edit" class="btn btn-info" data-toggle="modal" data-target="#hookEditModal" data-id="${v.id}">Edit</a>
            <a href="/${v.id}" id="btn${count}-del" class="btn btn-danger">Delete</a>
        </th>
    </tr`)

    $(`#btn${count}-del`).click(function (e) {
        e.preventDefault()
        const hook_id = v.id
        call('delete', '/' + hook_id, null, function () {
            $(`#table-${hook_id}`).remove()
        })
    })
}

function getEnumValue(num, mapping) {
    var res = []
    var arr = []
    for (k in mapping) {
        arr.push([k, mapping[k]])
    }
    arr.reverse()
    arr.forEach((v, i) => {
        if (v[1] > num) {
            return
        }
        num -= v[1]
        res.push(v[0])
    })
    return res
}

function getFormData($form) {
    var form_data = $form.serializeArray();
    var js = {
        mode: 0,
        status: 0
    };

    $.map(form_data, function (n, i) {

        if (n['name'] in mode_mapping) {
            js.mode += mode_mapping[n['name']]
        } else {
            js.status += status_mapping[n['name']]
        }
    });

    return js;
}

function call(method, url, data, cb) {
    axios({
        method: method,
        url: url,
        data: data
    }).then(function (resp) {
        $("#alerts").append(`<div class="alert alert-success"><button type="button" class="close" data-dismiss="alert">&times;</button><strong>Done!</strong></div>`)
    }).catch(function (error) {
        if (error.response) {
            $("#alerts").append(`<div class="alert alert-danger"><button type="button" class="close" data-dismiss="alert">&times;</button><strong>Error!</strong> ${error.response.data.err}.</div>`)
        } else {
            $("#alerts").append(`<div class="alert alert-danger"><button type="button" class="close" data-dismiss="alert">&times;</button><strong>Error!</strong> ${error.message}.</div>`)
        }
    }).finally(function () {
        if (cb) {
            cb()
        } else {
            return
        }
    });
}

var on_submit = function (e) {
    e.preventDefault()

    var formData = getFormData($('#form_data'))
    formData['hook_url'] = $("#hookurl").val()
    var $this = $(this)
    var orig = $this.html()
    $this.html('<i class="spinner-border spinner-border-sm"></i> Submitting...')
    $("#submithook").prop('disabled', true)

    call('post', '/add', formData, function () {
        $this.html(orig)
        load_list()
        $("#submithook").prop('disabled', false)
    })
}

var on_test = function (e) {
    e.preventDefault()

    var formData = getFormData($('#form_data'))
    formData['hook_url'] = $("#hookurl").val()

    var $this = $(this)
    var orig = $this.html()
    $this.html('<i class="spinner-border spinner-border-sm"></i> Testing...')
    $("#testhook").prop('disabled', true)

    call('post', '/test', formData, function () {
        $this.html(orig)
        $("#testhook").prop('disabled', false)
    })
}

$("#submithook").click(on_submit)

$("#testhook").click(on_test)

$('#hookEditModal').on('show.bs.modal', function (event) {
    $("#form_data_edit")[0].reset()
    var button = $(event.relatedTarget)
    var hook_id = button.data('id')
    var hook_data = owned_hooks[hook_id]
    var modal = $(this)
    modal.find('#hookurledit').val(hook_data.url)
    var enabled = getEnumValue(hook_data.mode, mode_mapping).concat(getEnumValue(hook_data.push_status, status_mapping))

    enabled.forEach(function (v, i) {
        var $field = modal.find('[name=' + v + ']')
        $field.first().prop("checked", true)
    })

    $("#btn-send").click(function () {
        var formData = getFormData($('#form_data_edit'))
        var $this = $(this)
        var orig = $this.html()
        $this.html('<i class="spinner-border spinner-border-sm"></i> Sending...')
    
        call('patch', '/' + hook_id, formData, function () {
            $this.html(orig)
            modal.modal('hide')
            load_list()
        })
    })
})

$('#hookEditModal').on('hide.bs.modal', function(e){
    $("#btn-send").unbind('click')
})

function load_list() {
    if ($('#login').length) {
        return
    } else {
        count = 0
        $("#table-content").empty()
        axios.get('/list').then(function (res) {
            res.data.forEach((v, i) => {
                add_data(v)
            })
        })
    }
}

$(document).ready(load_list)