const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadScript(relativePath, context) {
    const fullPath = path.join(__dirname, '..', relativePath);
    const code = fs.readFileSync(fullPath, 'utf8');
    vm.runInNewContext(code, context, { filename: relativePath });
}

test('缺陷详情中的用户输入会被转义', async () => {
    const context = {
        console,
        Date,
        window: {
            MiniAgile: {
                modals: {},
                nextTick: (fn) => fn && fn()
            }
        }
    };

    loadScript('static/js/app.modals.bug.js', context);

    let renderedHtml = '';
    const fakeContext = {
        api: async () => ({
            bug: {
                id: 1,
                title: '<img src=x onerror=alert(1)>',
                description: '<script>alert("bug")</script>',
                severity: 3,
                status: 'open',
                evidence_count: 1,
                latest_stack_trace: '<svg/onload=alert(2)>',
                time_spent: 0,
                time_estimate: 0,
                created_at: '2026-03-23T10:00:00',
                updated_at: '2026-03-23T10:00:00',
                reporter_name: 'tester',
                assignee_name: null
            },
            evidences: [{
                creator_name: 'tester',
                created_at: '2026-03-23T10:00:00',
                comment: '<script>alert("evidence")</script>',
                stack_trace: '<b>boom</b>',
                attachments: [{
                    url: '/static/uploads/demo.png',
                    file_name: '<script>alert("file")</script>'
                }]
            }],
            work_logs: []
        }),
        modalShow(html) {
            renderedHtml = html;
        }
    };

    await context.window.MiniAgile.modals.modalViewBug.call(fakeContext, 1);

    assert.ok(renderedHtml.includes('&lt;script&gt;alert(&quot;evidence&quot;)&lt;/script&gt;'));
    assert.ok(renderedHtml.includes('&lt;img src=x onerror=alert(1)&gt;'));
    assert.ok(renderedHtml.includes('&lt;svg/onload=alert(2)&gt;'));
    assert.ok(renderedHtml.includes('&lt;script&gt;alert(&quot;file&quot;)&lt;/script&gt;'));

    assert.ok(!renderedHtml.includes('<script>alert("evidence")</script>'));
    assert.ok(!renderedHtml.includes('<img src=x onerror=alert(1)>'));
    assert.ok(!renderedHtml.includes('<svg/onload=alert(2)>'));
});
