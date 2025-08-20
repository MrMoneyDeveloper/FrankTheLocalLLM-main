describe('Full flow', () => {
  it('loads wiki and chats', () => {
    cy.intercept('POST', '/api/chat', {
      body: { response: 'hi there', cached: false }
    })
    cy.visit('/')
    cy.get('input[placeholder="Say hi"]').type('hello')
    cy.contains('Send').click()
    // chat request is mocked above
  })
})
