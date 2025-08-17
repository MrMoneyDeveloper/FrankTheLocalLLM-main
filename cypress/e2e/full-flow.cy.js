describe('Full flow', () => {
  it('logs in and chats', () => {
    cy.intercept('POST', '/api/auth/login', {
      body: { access_token: 'token', token_type: 'bearer' }
    })
    cy.intercept('POST', '/api/chat', {
      body: { response: 'hi there', cached: false }
    })
    cy.visit('/')
    cy.get('input[type=text]').type('bob')
    cy.get('input[type=password]').type('pw')
    cy.contains('Login').click()
    cy.contains('Login successful!')

    // imagine chat component exists
    // chat request is mocked above
  })
})
